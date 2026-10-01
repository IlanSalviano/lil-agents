import AVFoundation
import AppKit

enum CharacterSize: String, CaseIterable {
    case large, medium, small
    var height: CGFloat {
        switch self {
        case .large: return 200
        case .medium: return 150
        case .small: return 100
        }
    }
    var displayName: String {
        switch self {
        case .large: return "Large"
        case .medium: return "Medium"
        case .small: return "Small"
        }
    }
}

/// One-shot special attack clip (e.g. Thunder Breathing forms).
struct SpecialMove {
    var videoName: String
    /// Total clip length used for finish timing.
    var duration: CFTimeInterval?
    /// When during the clip the character snaps to the end position.
    var dashAt: CFTimeInterval?
    var travelRange: ClosedRange<CGFloat>?
    var sizeScale: CGFloat?
}

class WalkerCharacter {
    let videoName: String
    let name: String
    var provider: AgentProvider {
        get {
            let raw = UserDefaults.standard.string(forKey: "\(name)Provider") ?? "claude"
            return AgentProvider(rawValue: raw) ?? .claude
        }
        set {
            UserDefaults.standard.set(newValue.rawValue, forKey: "\(name)Provider")
        }
    }
    var size: CharacterSize {
        get {
            let raw = UserDefaults.standard.string(forKey: "\(name)Size") ?? "big"
            return CharacterSize(rawValue: raw) ?? .large
        }
        set {
            UserDefaults.standard.set(newValue.rawValue, forKey: "\(name)Size")
            updateDimensions()
        }
    }
    var window: NSWindow!
    var playerLayer: AVPlayerLayer!
    var queuePlayer: AVQueuePlayer!
    var looper: AVPlayerLooper!

    let videoWidth: CGFloat = 1080
    let videoHeight: CGFloat = 1920
    private(set) var displayHeight: CGFloat = 200
    var displayWidth: CGFloat { displayHeight * (videoWidth / videoHeight) }

    // Walk timing (per-character, from frame analysis)
    let videoDuration: CFTimeInterval = 10.0
    var accelStart: CFTimeInterval = 3.0
    var fullSpeedStart: CFTimeInterval = 3.75
    var decelStart: CFTimeInterval = 7.5
    var walkStop: CFTimeInterval = 8.25
    var walkAmountRange: ClosedRange<CGFloat> = 0.25...0.5
    var yOffset: CGFloat = 0
    var flipXOffset: CGFloat = 0
    var characterColor: NSColor = .gray

    // Walk state
    var playCount = 0
    var walkStartTime: CFTimeInterval = 0
    var positionProgress: CGFloat = 0.0
    var isWalking = false
    var isPaused = true
    var pauseEndTime: CFTimeInterval = 0
    var goingRight = true
    var walkStartPos: CGFloat = 0.0
    var walkEndPos: CGFloat = 0.0
    var currentTravelDistance: CGFloat = 500.0
    // Walk endpoints stored in pixels for consistent speed across screen switches
    var walkStartPixel: CGFloat = 0.0
    var walkEndPixel: CGFloat = 0.0

    // Special moves (e.g. Thunder Breath, Flaming Thunder God) — one-shot videos + position snap
    /// Prefer `specialMoves`; `specialVideoName` is a convenience for a single special.
    var specialMoves: [SpecialMove] = []
    var specialVideoName: String? {
        get { specialMoves.first?.videoName }
        set {
            guard let name = newValue, !name.isEmpty else {
                specialMoves = []
                return
            }
            if specialMoves.isEmpty {
                specialMoves = [SpecialMove(videoName: name)]
            } else {
                specialMoves[0].videoName = name
            }
        }
    }
    var specialChance: Double = 0
    var specialDuration: CFTimeInterval = 2.5
    /// Elapsed time in the special clip when the character blinks to the end position.
    var specialDashAt: CFTimeInterval = 0.7
    var specialTravelRange: ClosedRange<CGFloat> = 0.45...0.85
    /// Default window scale while a special plays (overridable per `SpecialMove.sizeScale`).
    var specialSizeScale: CGFloat = 1.0
    var isPlayingSpecial = false
    private var specialStartTime: CFTimeInterval = 0
    private var specialHasDashed = false
    private var isSpecialPresentationActive = false
    /// Active special timing / scale (copied from the chosen move when it starts).
    private var activeSpecialDuration: CFTimeInterval = 2.5
    private var activeSpecialDashAt: CFTimeInterval = 0.7
    private var activeSpecialSizeScale: CGFloat = 1.0

    // Onboarding
    var isOnboarding = false

    // Popover state
    var isIdleForPopover = false
    var popoverWindow: NSWindow?
    var terminalView: TerminalView?
    var session: (any AgentSession)?
    var clickOutsideMonitor: Any?
    var escapeKeyMonitor: Any?
    var currentStreamingText = ""
    weak var controller: LilAgentsController?
    var themeOverride: PopoverTheme?
    var isAgentBusy: Bool { session?.isBusy ?? false }
    var thinkingBubbleWindow: NSWindow?
    private(set) var isManuallyVisible = true
    private var environmentHiddenAt: CFTimeInterval?
    private var wasPopoverVisibleBeforeEnvironmentHide = false
    private var wasBubbleVisibleBeforeEnvironmentHide = false

    init(videoName: String, name: String) {
        self.videoName = videoName
        self.name = name
        self.displayHeight = size.height
    }

    // MARK: - Setup

    func updateDimensions() {
        // Keep special enlarged presentation if a special is mid-play.
        let scale = isSpecialPresentationActive ? max(activeSpecialSizeScale, 1.0) : 1.0
        displayHeight = size.height * scale
        applyWindowSize(width: displayWidth, height: displayHeight, expandUpward: scale > 1.0)
    }

    /// Resize the character window. When `expandUpward` is true, extra height grows above the dock
    /// so feet stay put while special FX get more room.
    private func applyWindowSize(width: CGFloat, height: CGFloat, expandUpward: Bool) {
        DispatchQueue.main.async { [weak self] in
            guard let self = self, let window = self.window else { return }
            let old = window.frame
            var origin = old.origin
            if expandUpward {
                // AppKit y is bottom edge — same origin grows upward.
                origin.y = old.origin.y
                // Center horizontally around previous center so the character doesn't jump sideways.
                let oldCenterX = old.origin.x + old.width / 2
                origin.x = oldCenterX - width / 2
            }
            let newFrame = CGRect(x: origin.x, y: origin.y, width: width, height: height)

            CATransaction.begin()
            CATransaction.setDisableActions(true)
            window.setFrame(newFrame, display: true)
            self.playerLayer.frame = CGRect(x: 0, y: 0, width: width, height: height)
            if let hostView = window.contentView {
                hostView.frame = CGRect(x: 0, y: 0, width: width, height: height)
            }
            CATransaction.commit()

            self.updateFlip()
        }
    }

    private func setSpecialPresentation(_ active: Bool) {
        let scale = active ? max(activeSpecialSizeScale, 1.0) : 1.0
        // Always leave special presentation when deactivating; enlarge only when scale > 1.
        if active && scale <= 1.001 {
            isSpecialPresentationActive = false
            displayHeight = size.height
            applyWindowSize(width: displayWidth, height: displayHeight, expandUpward: false)
            return
        }
        isSpecialPresentationActive = active
        displayHeight = size.height * scale
        applyWindowSize(width: displayWidth, height: displayHeight, expandUpward: active)
    }

    func setup() {
        guard let videoURL = Bundle.main.url(forResource: videoName, withExtension: "mov") else {
            print("Video \(videoName) not found")
            return
        }

        let asset = AVAsset(url: videoURL)
        queuePlayer = AVQueuePlayer()
        looper = AVPlayerLooper(player: queuePlayer, templateItem: AVPlayerItem(asset: asset))

        playerLayer = AVPlayerLayer(player: queuePlayer)
        playerLayer.videoGravity = .resizeAspect
        playerLayer.backgroundColor = NSColor.clear.cgColor
        playerLayer.frame = CGRect(x: 0, y: 0, width: displayWidth, height: displayHeight)

        let screen = NSScreen.main!
        let dockTopY = screen.visibleFrame.origin.y
        let bottomPadding = displayHeight * 0.15
        let y = dockTopY - bottomPadding + yOffset

        let contentRect = CGRect(x: 0, y: y, width: displayWidth, height: displayHeight)
        window = NSWindow(
            contentRect: contentRect,
            styleMask: .borderless,
            backing: .buffered,
            defer: false
        )
        window.isOpaque = false
        window.backgroundColor = .clear
        window.hasShadow = false
        window.level = .statusBar
        window.ignoresMouseEvents = false
        window.collectionBehavior = [.moveToActiveSpace, .stationary]

        let hostView = CharacterContentView(frame: CGRect(x: 0, y: 0, width: displayWidth, height: displayHeight))
        hostView.character = self
        hostView.wantsLayer = true
        hostView.layer?.backgroundColor = NSColor.clear.cgColor
        hostView.layer?.addSublayer(playerLayer)

        window.contentView = hostView
        window.orderFrontRegardless()
    }

    // MARK: - Visibility

    func setManuallyVisible(_ visible: Bool) {
        isManuallyVisible = visible
        if visible {
            if environmentHiddenAt == nil {
                window.orderFrontRegardless()
            }
        } else {
            queuePlayer.pause()
            window.orderOut(nil)
            popoverWindow?.orderOut(nil)
            thinkingBubbleWindow?.orderOut(nil)
        }
    }

    func hideForEnvironment() {
        guard environmentHiddenAt == nil else { return }

        environmentHiddenAt = CACurrentMediaTime()
        wasPopoverVisibleBeforeEnvironmentHide = popoverWindow?.isVisible ?? false
        wasBubbleVisibleBeforeEnvironmentHide = thinkingBubbleWindow?.isVisible ?? false

        queuePlayer.pause()
        window.orderOut(nil)
        popoverWindow?.orderOut(nil)
        thinkingBubbleWindow?.orderOut(nil)
    }

    func showForEnvironmentIfNeeded() {
        guard let hiddenAt = environmentHiddenAt else { return }

        let hiddenDuration = CACurrentMediaTime() - hiddenAt
        environmentHiddenAt = nil
        walkStartTime += hiddenDuration
        pauseEndTime += hiddenDuration
        completionBubbleExpiry += hiddenDuration
        lastPhraseUpdate += hiddenDuration

        guard isManuallyVisible else { return }

        window.orderFrontRegardless()
        if isWalking || isPlayingSpecial {
            queuePlayer.play()
        }

        if isIdleForPopover && wasPopoverVisibleBeforeEnvironmentHide {
            updatePopoverPosition()
            popoverWindow?.orderFrontRegardless()
            popoverWindow?.makeKey()
            if let terminal = terminalView {
                popoverWindow?.makeFirstResponder(terminal.inputField)
            }
        }

        if wasBubbleVisibleBeforeEnvironmentHide {
            updateThinkingBubble()
        }
    }

    // MARK: - Click Handling & Popover

    func handleClick() {
        if isOnboarding {
            openOnboardingPopover()
            return
        }
        if isIdleForPopover {
            closePopover()
        } else {
            openPopover()
        }
    }

    private func openOnboardingPopover() {
        showingCompletion = false
        hideBubble()

        if isPlayingSpecial {
            finishSpecial(restoreWalk: true)
        }

        isIdleForPopover = true
        isWalking = false
        isPaused = true
        queuePlayer.pause()
        queuePlayer.seek(to: .zero)

        if popoverWindow == nil {
            createPopoverWindow()
        }

        // Show static welcome message instead of Claude terminal
        terminalView?.inputField.isEditable = false
        terminalView?.inputField.placeholderString = ""
        let welcome = """
        hey! we're bruce, jazz, and zenitsu — your lil dock agents.

        click any of us to open a Claude AI chat. we'll walk around while you work and let you know when Claude's thinking.

        check the menu bar icon (top right) for themes, sounds, and more options.

        click anywhere outside to dismiss, then click us again to start chatting.
        """
        terminalView?.appendStreamingText(welcome)
        terminalView?.endStreaming()

        updatePopoverPosition()
        popoverWindow?.orderFrontRegardless()

        // Set up click-outside to dismiss and complete onboarding
        clickOutsideMonitor = NSEvent.addGlobalMonitorForEvents(matching: .leftMouseDown) { [weak self] _ in
            self?.closeOnboarding()
        }
        escapeKeyMonitor = NSEvent.addLocalMonitorForEvents(matching: .keyDown) { [weak self] event in
            if event.keyCode == 53 { self?.closeOnboarding(); return nil }
            return event
        }
    }

    private func closeOnboarding() {
        if let monitor = clickOutsideMonitor { NSEvent.removeMonitor(monitor); clickOutsideMonitor = nil }
        if let monitor = escapeKeyMonitor { NSEvent.removeMonitor(monitor); escapeKeyMonitor = nil }
        popoverWindow?.orderOut(nil)
        popoverWindow = nil
        terminalView = nil
        isIdleForPopover = false
        isOnboarding = false
        isPaused = true
        pauseEndTime = CACurrentMediaTime() + Double.random(in: 1.0...3.0)
        queuePlayer.seek(to: .zero)
        controller?.completeOnboarding()
    }

    func openPopover() {
        // Close any other open popover
        if let siblings = controller?.characters {
            for sibling in siblings where sibling !== self && sibling.isIdleForPopover {
                sibling.closePopover()
            }
        }

        if isPlayingSpecial {
            finishSpecial(restoreWalk: true)
        }

        isIdleForPopover = true
        isWalking = false
        isPaused = true
        queuePlayer.pause()
        queuePlayer.seek(to: .zero)

        // Always clear any bubble (thinking or completion) when popover opens
        showingCompletion = false
        hideBubble()

        if session == nil {
            let newSession = provider.createSession()
            session = newSession
            wireSession(newSession)
            newSession.start()
        }

        if popoverWindow == nil {
            createPopoverWindow()
        }

        if let terminal = terminalView, let session = session, !session.history.isEmpty {
            terminal.replayHistory(session.history)
        }

        updatePopoverPosition()
        popoverWindow?.orderFrontRegardless()
        popoverWindow?.makeKey()

        if let terminal = terminalView {
            popoverWindow?.makeFirstResponder(terminal.inputField)
        }

        // Remove old monitors before adding new ones
        removeEventMonitors()

        clickOutsideMonitor = NSEvent.addGlobalMonitorForEvents(matching: [.leftMouseDown, .rightMouseDown]) { [weak self] event in
            guard let self = self, let popover = self.popoverWindow else { return }
            let popoverFrame = popover.frame
            let charFrame = self.window.frame
            if !popoverFrame.contains(NSEvent.mouseLocation) && !charFrame.contains(NSEvent.mouseLocation) {
                self.closePopover()
            }
        }

        escapeKeyMonitor = NSEvent.addLocalMonitorForEvents(matching: .keyDown) { [weak self] event in
            if event.keyCode == 53 {
                self?.closePopover()
                return nil
            }
            return event
        }
    }

    func closePopover() {
        guard isIdleForPopover else { return }

        popoverWindow?.orderOut(nil)
        removeEventMonitors()

        isIdleForPopover = false

        // If still waiting for a response, show thinking bubble immediately
        // If completion came while popover was open, show completion bubble
        if showingCompletion {
            // Reset expiry so user gets the full 3s from now
            completionBubbleExpiry = CACurrentMediaTime() + 3.0
            showBubble(text: currentPhrase, isCompletion: true)
        } else if isAgentBusy {
            // Force a fresh phrase pick and show immediately
            currentPhrase = ""
            lastPhraseUpdate = 0
            updateThinkingPhrase()
            showBubble(text: currentPhrase, isCompletion: false)
        }

        let delay = Double.random(in: 2.0...5.0)
        pauseEndTime = CACurrentMediaTime() + delay
    }

    private func removeEventMonitors() {
        if let monitor = clickOutsideMonitor {
            NSEvent.removeMonitor(monitor)
            clickOutsideMonitor = nil
        }
        if let monitor = escapeKeyMonitor {
            NSEvent.removeMonitor(monitor)
            escapeKeyMonitor = nil
        }
    }

    var resolvedTheme: PopoverTheme {
        (themeOverride ?? PopoverTheme.current).withCharacterColor(characterColor).withCustomFont()
    }

    func createPopoverWindow() {
        let t = resolvedTheme
        let popoverWidth: CGFloat = 420
        let popoverHeight: CGFloat = 310

        let win = KeyableWindow(
            contentRect: CGRect(x: 0, y: 0, width: popoverWidth, height: popoverHeight),
            styleMask: .borderless,
            backing: .buffered,
            defer: false
        )
        win.isOpaque = false
        win.backgroundColor = .clear
        win.hasShadow = true
        win.level = NSWindow.Level(rawValue: NSWindow.Level.statusBar.rawValue + 10)
        win.collectionBehavior = [.moveToActiveSpace, .stationary]
        let brightness = t.popoverBg.redComponent * 0.299 + t.popoverBg.greenComponent * 0.587 + t.popoverBg.blueComponent * 0.114
        win.appearance = NSAppearance(named: brightness < 0.5 ? .darkAqua : .aqua)

        let container = NSView(frame: NSRect(x: 0, y: 0, width: popoverWidth, height: popoverHeight))
        container.wantsLayer = true
        container.layer?.backgroundColor = t.popoverBg.cgColor
        container.layer?.cornerRadius = t.popoverCornerRadius
        container.layer?.masksToBounds = true
        container.layer?.borderWidth = t.popoverBorderWidth
        container.layer?.borderColor = t.popoverBorder.cgColor
        container.autoresizingMask = [.width, .height]

        let titleBar = NSView(frame: NSRect(x: 0, y: popoverHeight - 28, width: popoverWidth, height: 28))
        titleBar.wantsLayer = true
        titleBar.layer?.backgroundColor = t.titleBarBg.cgColor
        container.addSubview(titleBar)

        let titleLabel = NSTextField(labelWithString: t.titleString(for: provider))
        titleLabel.font = t.titleFont
        titleLabel.textColor = t.titleText
        titleLabel.sizeToFit()
        titleLabel.frame.origin = NSPoint(x: 12, y: 6)
        titleBar.addSubview(titleLabel)

        let arrowBtn = NSButton(frame: NSRect(x: titleLabel.frame.maxX + 2, y: 5, width: 16, height: 16))
        arrowBtn.image = NSImage(systemSymbolName: "chevron.down", accessibilityDescription: "Switch provider")
        arrowBtn.imageScaling = .scaleProportionallyDown
        arrowBtn.bezelStyle = .inline
        arrowBtn.isBordered = false
        arrowBtn.contentTintColor = t.titleText.withAlphaComponent(0.75)
        arrowBtn.target = self
        arrowBtn.action = #selector(showProviderMenu(_:))
        titleBar.addSubview(arrowBtn)

        // Make the title label clickable too
        let clickArea = NSButton(frame: NSRect(x: 0, y: 0, width: arrowBtn.frame.maxX + 4, height: 28))
        clickArea.isTransparent = true
        clickArea.target = self
        clickArea.action = #selector(showProviderMenu(_:))
        titleBar.addSubview(clickArea)

        let refreshBtn = NSButton(frame: NSRect(x: popoverWidth - 48, y: 5, width: 16, height: 16))
        refreshBtn.image = NSImage(systemSymbolName: "arrow.clockwise", accessibilityDescription: "Refresh")
        refreshBtn.imageScaling = .scaleProportionallyDown
        refreshBtn.bezelStyle = .inline
        refreshBtn.isBordered = false
        refreshBtn.contentTintColor = t.titleText.withAlphaComponent(0.75)
        refreshBtn.target = self
        refreshBtn.action = #selector(refreshSessionFromButton)
        titleBar.addSubview(refreshBtn)

        let copyBtn = NSButton(frame: NSRect(x: popoverWidth - 28, y: 5, width: 16, height: 16))
        copyBtn.image = NSImage(systemSymbolName: "square.on.square", accessibilityDescription: "Copy")
        copyBtn.imageScaling = .scaleProportionallyDown
        copyBtn.bezelStyle = .inline
        copyBtn.isBordered = false
        copyBtn.contentTintColor = t.titleText.withAlphaComponent(0.75)
        copyBtn.target = self
        copyBtn.action = #selector(copyLastResponseFromButton)
        titleBar.addSubview(copyBtn)

        let sep = NSView(frame: NSRect(x: 0, y: popoverHeight - 29, width: popoverWidth, height: 1))
        sep.wantsLayer = true
        sep.layer?.backgroundColor = t.separatorColor.cgColor
        container.addSubview(sep)

        let terminal = TerminalView(frame: NSRect(x: 0, y: 0, width: popoverWidth, height: popoverHeight - 29))
        terminal.characterColor = characterColor
        terminal.themeOverride = themeOverride
        terminal.provider = provider
        terminal.autoresizingMask = [.width, .height]
        terminal.onSendMessage = { [weak self] message in
            self?.session?.send(message: message)
        }
        terminal.onClearRequested = { [weak self] in
            self?.resetSession()
        }
        container.addSubview(terminal)

        win.contentView = container
        popoverWindow = win
        terminalView = terminal
    }

    func resetSession() {
        session?.terminate()
        session = nil
        currentStreamingText = ""
        showingCompletion = false
        currentPhrase = ""
        completionBubbleExpiry = 0
        hideBubble()
        terminalView?.resetState()
        terminalView?.showSessionMessage()
        let newSession = provider.createSession()
        session = newSession
        wireSession(newSession)
        newSession.start()
    }

    private func wireSession(_ session: any AgentSession) {
        session.onText = { [weak self] text in
            self?.currentStreamingText += text
            self?.terminalView?.appendStreamingText(text)
        }

        session.onTurnComplete = { [weak self] in
            self?.terminalView?.endStreaming()
            self?.playCompletionSound()
            self?.showCompletionBubble()
        }

        session.onError = { [weak self] text in
            self?.terminalView?.appendError(text)
        }

        session.onToolUse = { [weak self] toolName, input in
            guard let self = self else { return }
            let summary = self.formatToolInput(input)
            self.terminalView?.appendToolUse(toolName: toolName, summary: summary)
        }

        session.onToolResult = { [weak self] summary, isError in
            self?.terminalView?.appendToolResult(summary: summary, isError: isError)
        }

        session.onProcessExit = { [weak self] in
            guard let self = self else { return }
            self.terminalView?.endStreaming()
            self.terminalView?.appendError("\(self.provider.displayName) session ended.")
        }

        session.onSessionReady = { }
    }

    @objc func showProviderMenu(_ sender: Any) {
        let menu = NSMenu()
        let menuFont = NSFont.systemFont(ofSize: 12, weight: .regular)
        for p in AgentProvider.allCases {
            let item = NSMenuItem(title: p.displayName, action: #selector(providerMenuItemSelected(_:)), keyEquivalent: "")
            item.target = self
            item.attributedTitle = NSAttributedString(string: p.displayName, attributes: [.font: menuFont])
            item.representedObject = p.rawValue
            if p == provider {
                item.state = .on
            }
            if !p.isAvailable {
                item.isEnabled = false
            }
            menu.addItem(item)
        }
        // Show menu below the title bar area
        if let titleBar = popoverWindow?.contentView?.subviews.first(where: { $0.frame.origin.y > 0 && $0.frame.height == 28 }) {
            menu.popUp(positioning: nil, at: NSPoint(x: 10, y: 0), in: titleBar)
        }
    }

    @objc func providerMenuItemSelected(_ sender: NSMenuItem) {
        guard let raw = sender.representedObject as? String,
              let newProvider = AgentProvider(rawValue: raw),
              newProvider != provider else { return }
        provider = newProvider
        // Terminate existing session and rebuild popover for new provider
        session?.terminate()
        session = nil
        popoverWindow?.orderOut(nil)
        popoverWindow = nil
        terminalView = nil
        thinkingBubbleWindow?.orderOut(nil)
        thinkingBubbleWindow = nil
        openPopover()
    }

    @objc func copyLastResponseFromButton() {
        terminalView?.handleSlashCommandPublic("/copy")
    }

    @objc func refreshSessionFromButton() {
        guard !isOnboarding else { return }
        resetSession()
    }

    private func formatToolInput(_ input: [String: Any]) -> String {
        if let cmd = input["command"] as? String { return cmd }
        if let path = input["file_path"] as? String { return path }
        if let pattern = input["pattern"] as? String { return pattern }
        return input.keys.sorted().prefix(3).joined(separator: ", ")
    }

    func updatePopoverPosition() {
        guard let popover = popoverWindow, isIdleForPopover else { return }
        guard let screen = NSScreen.main else { return }

        let charFrame = window.frame
        let popoverSize = popover.frame.size
        var x = charFrame.midX - popoverSize.width / 2
        let y = charFrame.maxY - 15

        let screenFrame = screen.frame
        x = max(screenFrame.minX + 4, min(x, screenFrame.maxX - popoverSize.width - 4))
        let clampedY = min(y, screenFrame.maxY - popoverSize.height - 4)

        popover.setFrameOrigin(NSPoint(x: x, y: clampedY))
    }

    // MARK: - Thinking Bubble

    private static let thinkingPhrases = [
        "hmm...", "thinking...", "one sec...", "ok hold on",
        "let me check", "working on it", "almost...", "bear with me",
        "on it!", "gimme a sec", "brb", "processing...",
        "hang tight", "just a moment", "figuring it out",
        "crunching...", "reading...", "looking...",
        "cooking...", "vibing...", "digging in",
        "connecting dots", "give me a sec",
        "don't rush me", "calculating...", "assembling\u{2026}"
    ]

    private static let completionPhrases = [
        "done!", "all set!", "ready!", "here you go", "got it!",
        "finished!", "ta-da!", "voila!",
        "boom!", "there ya go!", "check it out!"
    ]

    private var lastPhraseUpdate: CFTimeInterval = 0
    var currentPhrase = ""
    var completionBubbleExpiry: CFTimeInterval = 0
    var showingCompletion = false

    private static let bubbleH: CGFloat = 26
    private var phraseAnimating = false

    func updateThinkingBubble() {
        let now = CACurrentMediaTime()

        if showingCompletion {
            if now >= completionBubbleExpiry {
                showingCompletion = false
                hideBubble()
                return
            }
            if isIdleForPopover {
                completionBubbleExpiry += 1.0 / 60.0
                hideBubble()
            } else {
                showBubble(text: currentPhrase, isCompletion: true)
            }
            return
        }

        if isAgentBusy && !isIdleForPopover {
            let oldPhrase = currentPhrase
            updateThinkingPhrase()
            if currentPhrase != oldPhrase && !oldPhrase.isEmpty && !phraseAnimating {
                animatePhraseChange(to: currentPhrase, isCompletion: false)
            } else if !phraseAnimating {
                showBubble(text: currentPhrase, isCompletion: false)
            }
        } else if !showingCompletion {
            hideBubble()
        }
    }

    private func hideBubble() {
        if thinkingBubbleWindow?.isVisible ?? false {
            thinkingBubbleWindow?.orderOut(nil)
        }
    }

    private func animatePhraseChange(to newText: String, isCompletion: Bool) {
        guard let win = thinkingBubbleWindow, win.isVisible,
              let label = win.contentView?.viewWithTag(100) as? NSTextField else {
            showBubble(text: newText, isCompletion: isCompletion)
            return
        }
        phraseAnimating = true

        NSAnimationContext.runAnimationGroup({ ctx in
            ctx.duration = 0.2
            ctx.allowsImplicitAnimation = true
            label.animator().alphaValue = 0.0
        }, completionHandler: { [weak self] in
            self?.showBubble(text: newText, isCompletion: isCompletion)
            label.alphaValue = 0.0
            NSAnimationContext.runAnimationGroup({ ctx in
                ctx.duration = 0.25
                ctx.allowsImplicitAnimation = true
                label.animator().alphaValue = 1.0
            }, completionHandler: {
                self?.phraseAnimating = false
            })
        })
    }

    func showBubble(text: String, isCompletion: Bool) {
        let t = resolvedTheme
        if thinkingBubbleWindow == nil {
            createThinkingBubble()
        }

        let h = Self.bubbleH
        let padding: CGFloat = 16
        let font = t.bubbleFont
        let textSize = (text as NSString).size(withAttributes: [.font: font])
        let bubbleW = max(ceil(textSize.width) + padding * 2, 48)

        let charFrame = window.frame
        let x = charFrame.midX - bubbleW / 2
        let y = charFrame.origin.y + charFrame.height * 0.88
        thinkingBubbleWindow?.setFrame(CGRect(x: x, y: y, width: bubbleW, height: h), display: false)

        let borderColor = isCompletion ? t.bubbleCompletionBorder.cgColor : t.bubbleBorder.cgColor
        let textColor = isCompletion ? t.bubbleCompletionText : t.bubbleText

        if let container = thinkingBubbleWindow?.contentView {
            container.frame = NSRect(x: 0, y: 0, width: bubbleW, height: h)
            container.layer?.backgroundColor = t.bubbleBg.cgColor
            container.layer?.cornerRadius = t.bubbleCornerRadius
            container.layer?.borderColor = borderColor
            if let label = container.viewWithTag(100) as? NSTextField {
                label.font = font
                let lineH = ceil(textSize.height)
                let labelY = round((h - lineH) / 2) - 1
                label.frame = NSRect(x: 0, y: labelY, width: bubbleW, height: lineH + 2)
                label.stringValue = text
                label.textColor = textColor
            }
        }

        if !(thinkingBubbleWindow?.isVisible ?? false) {
            thinkingBubbleWindow?.alphaValue = 1.0
            thinkingBubbleWindow?.orderFrontRegardless()
        }
    }

    private func updateThinkingPhrase() {
        let now = CACurrentMediaTime()
        if currentPhrase.isEmpty || now - lastPhraseUpdate > Double.random(in: 3.0...5.0) {
            var next = Self.thinkingPhrases.randomElement() ?? "..."
            while next == currentPhrase && Self.thinkingPhrases.count > 1 {
                next = Self.thinkingPhrases.randomElement() ?? "..."
            }
            currentPhrase = next
            lastPhraseUpdate = now
        }
    }

    func showCompletionBubble() {
        currentPhrase = Self.completionPhrases.randomElement() ?? "done!"
        showingCompletion = true
        completionBubbleExpiry = CACurrentMediaTime() + 3.0
        lastPhraseUpdate = 0
        phraseAnimating = false
        if !isIdleForPopover {
            showBubble(text: currentPhrase, isCompletion: true)
        }
    }

    private func createThinkingBubble() {
        let t = resolvedTheme
        let w: CGFloat = 80
        let h = Self.bubbleH
        let win = NSWindow(
            contentRect: CGRect(x: 0, y: 0, width: w, height: h),
            styleMask: .borderless, backing: .buffered, defer: false
        )
        win.isOpaque = false
        win.backgroundColor = .clear
        win.hasShadow = true
        win.level = NSWindow.Level(rawValue: NSWindow.Level.statusBar.rawValue + 5)
        win.ignoresMouseEvents = true
        win.collectionBehavior = [.moveToActiveSpace, .stationary]

        let container = NSView(frame: NSRect(x: 0, y: 0, width: w, height: h))
        container.wantsLayer = true
        container.layer?.backgroundColor = t.bubbleBg.cgColor
        container.layer?.cornerRadius = t.bubbleCornerRadius
        container.layer?.borderWidth = 1
        container.layer?.borderColor = t.bubbleBorder.cgColor

        let font = t.bubbleFont
        let lineH = ceil(("Xg" as NSString).size(withAttributes: [.font: font]).height)
        let labelY = round((h - lineH) / 2) - 1

        let label = NSTextField(labelWithString: "")
        label.font = font
        label.textColor = t.bubbleText
        label.alignment = .center
        label.drawsBackground = false
        label.isBordered = false
        label.isEditable = false
        label.frame = NSRect(x: 0, y: labelY, width: w, height: lineH + 2)
        label.tag = 100
        container.addSubview(label)

        win.contentView = container
        thinkingBubbleWindow = win
    }

    // MARK: - Completion Sound

    static var soundsEnabled = true

    private static let completionSounds: [(name: String, ext: String)] = [
        ("ping-aa", "mp3"), ("ping-bb", "mp3"), ("ping-cc", "mp3"),
        ("ping-dd", "mp3"), ("ping-ee", "mp3"), ("ping-ff", "mp3"),
        ("ping-gg", "mp3"), ("ping-hh", "mp3"), ("ping-jj", "m4a")
    ]
    private static var lastSoundIndex: Int = -1

    func playCompletionSound() {
        guard Self.soundsEnabled else { return }
        var idx: Int
        repeat {
            idx = Int.random(in: 0..<Self.completionSounds.count)
        } while idx == Self.lastSoundIndex && Self.completionSounds.count > 1
        Self.lastSoundIndex = idx

        let s = Self.completionSounds[idx]
        if let url = Bundle.main.url(forResource: s.name, withExtension: s.ext, subdirectory: "Sounds"),
           let sound = NSSound(contentsOf: url, byReference: true) {
            sound.play()
        }
    }

    // MARK: - Walking

    /// Called when a pause ends — either a normal walk or a special move.
    func beginMovement() {
        if !specialMoves.isEmpty,
           specialChance > 0,
           Double.random(in: 0..<1) < specialChance {
            startSpecial()
        } else {
            startWalk()
        }
    }

    func startWalk() {
        isPaused = false
        isWalking = true
        isPlayingSpecial = false
        playCount = 0
        walkStartTime = CACurrentMediaTime()

        if positionProgress > 0.85 {
            goingRight = false
        } else if positionProgress < 0.15 {
            goingRight = true
        } else {
            goingRight = Bool.random()
        }

        walkStartPos = positionProgress
        // Walk a fixed pixel distance (~200-325px) regardless of screen width.
        // Use a safe travel distance so we never bake start==end pixels (which freezes dock X).
        let travel = max(currentTravelDistance, 1)
        let referenceWidth: CGFloat = 500.0
        let walkPixels = CGFloat.random(in: walkAmountRange) * referenceWidth
        let walkAmount = walkPixels / travel

        walkEndPos = targetPosition(from: walkStartPos, amount: walkAmount, preferRight: goingRight)
        if abs(walkEndPos - walkStartPos) < 0.01 {
            let flipped = targetPosition(from: walkStartPos, amount: walkAmount, preferRight: !goingRight)
            if abs(flipped - walkStartPos) > abs(walkEndPos - walkStartPos) {
                goingRight = !goingRight
                walkEndPos = flipped
            }
        }
        // Guarantee a visible dock slide even when siblings squeeze the path.
        if abs(walkEndPos - walkStartPos) * travel < 60 {
            let dir: CGFloat = goingRight ? 1 : -1
            walkEndPos = min(max(walkStartPos + dir * min(0.12, walkAmount), 0), 1)
            if abs(walkEndPos - walkStartPos) * travel < 40 {
                goingRight.toggle()
                let dir2: CGFloat = goingRight ? 1 : -1
                walkEndPos = min(max(walkStartPos + dir2 * 0.12, 0), 1)
            }
        }

        // Store pixel positions so walk speed stays consistent if screen changes mid-walk
        walkStartPixel = walkStartPos * travel
        walkEndPixel = walkEndPos * travel

        updateFlip()
        // Always leave special presentation before a normal walk.
        setSpecialPresentation(false)
        ensureWalkLooperPlaying()
    }

    func enterPause() {
        isWalking = false
        isPlayingSpecial = false
        isPaused = true
        queuePlayer.pause()
        queuePlayer.seek(to: .zero)
        let delay = Double.random(in: 5.0...12.0)
        pauseEndTime = CACurrentMediaTime() + delay
    }

    // MARK: - Special Move

    func startSpecial() {
        // Pick a random special whose video is present in the bundle.
        let available = specialMoves.compactMap { move -> (SpecialMove, URL)? in
            guard let url = Bundle.main.url(forResource: move.videoName, withExtension: "mov") else {
                return nil
            }
            return (move, url)
        }
        guard let (move, specialURL) = available.randomElement() else {
            startWalk()
            return
        }

        activeSpecialDuration = move.duration ?? specialDuration
        activeSpecialDashAt = move.dashAt ?? specialDashAt
        activeSpecialSizeScale = move.sizeScale ?? specialSizeScale
        let travelRange = move.travelRange ?? specialTravelRange

        isPaused = false
        isWalking = false
        isPlayingSpecial = true
        specialHasDashed = false
        specialStartTime = CACurrentMediaTime()

        if positionProgress > 0.7 {
            goingRight = false
        } else if positionProgress < 0.3 {
            goingRight = true
        } else {
            goingRight = Bool.random()
        }

        walkStartPos = positionProgress
        let travel = CGFloat.random(in: travelRange)
        walkEndPos = targetPosition(from: walkStartPos, amount: travel, preferRight: goingRight)
        if abs(walkEndPos - walkStartPos) < 0.08 {
            let flipped = targetPosition(from: walkStartPos, amount: travel, preferRight: !goingRight)
            if abs(flipped - walkStartPos) > abs(walkEndPos - walkStartPos) {
                goingRight = !goingRight
                walkEndPos = flipped
            }
        }
        walkStartPixel = walkStartPos * currentTravelDistance
        walkEndPixel = walkEndPos * currentTravelDistance

        updateFlip()
        setSpecialPresentation(true)
        playOneShot(url: specialURL)
    }

    private func finishSpecial(restoreWalk: Bool) {
        isPlayingSpecial = false
        specialHasDashed = false
        // Land at destination even if cancelled mid-anticipation
        positionProgress = walkEndPos
        setSpecialPresentation(false)
        if restoreWalk {
            restoreWalkLooper(paused: true)
        }
    }

    private func playOneShot(url: URL) {
        looper?.disableLooping()
        looper = nil
        queuePlayer.removeAllItems()
        let item = AVPlayerItem(url: url)
        queuePlayer.insert(item, after: nil)
        queuePlayer.seek(to: .zero)
        queuePlayer.play()
    }

    private func restoreWalkLooper(paused: Bool) {
        looper?.disableLooping()
        looper = nil
        queuePlayer.removeAllItems()
        guard let videoURL = Bundle.main.url(forResource: videoName, withExtension: "mov") else { return }
        let asset = AVAsset(url: videoURL)
        looper = AVPlayerLooper(player: queuePlayer, templateItem: AVPlayerItem(asset: asset))
        queuePlayer.seek(to: .zero)
        if paused {
            queuePlayer.pause()
        } else {
            queuePlayer.play()
        }
    }

    private func ensureWalkLooperPlaying() {
        if looper == nil {
            restoreWalkLooper(paused: false)
        } else {
            queuePlayer.seek(to: .zero)
            queuePlayer.play()
        }
    }

    /// Shared pathfinding toward a dock progress target, avoiding siblings.
    private func targetPosition(from start: CGFloat, amount: CGFloat, preferRight: Bool) -> CGFloat {
        let minSeparation: CGFloat = 0.12
        var end = preferRight ? min(start + amount, 1.0) : max(start - amount, 0.0)
        for sibling in controller?.characters ?? [] where sibling !== self {
            let sibPos = sibling.positionProgress
            guard abs(end - sibPos) < minSeparation else { continue }
            end = preferRight ? max(start, sibPos - minSeparation)
                              : min(start, sibPos + minSeparation)
        }
        return end
    }

    func updateFlip() {
        CATransaction.begin()
        CATransaction.setDisableActions(true)
        if goingRight {
            playerLayer.transform = CATransform3DIdentity
        } else {
            playerLayer.transform = CATransform3DMakeScale(-1, 1, 1)
        }
        playerLayer.frame = CGRect(x: 0, y: 0, width: displayWidth, height: displayHeight)
        CATransaction.commit()
    }

    var currentFlipCompensation: CGFloat {
        goingRight ? 0 : flipXOffset
    }

    func movementPosition(at videoTime: CFTimeInterval) -> CGFloat {
        let dIn = fullSpeedStart - accelStart
        let dLin = decelStart - fullSpeedStart
        let dOut = walkStop - decelStart
        let v = 1.0 / (dIn / 2.0 + dLin + dOut / 2.0)

        if videoTime <= accelStart {
            return 0.0
        } else if videoTime <= fullSpeedStart {
            let t = videoTime - accelStart
            return CGFloat(v * t * t / (2.0 * dIn))
        } else if videoTime <= decelStart {
            let easeInDist = v * dIn / 2.0
            let t = videoTime - fullSpeedStart
            return CGFloat(easeInDist + v * t)
        } else if videoTime <= walkStop {
            let easeInDist = v * dIn / 2.0
            let linearDist = v * dLin
            let t = videoTime - decelStart
            return CGFloat(easeInDist + linearDist + v * (t - t * t / (2.0 * dOut)))
        } else {
            return 1.0
        }
    }

    // MARK: - Frame Update

    func update(dockX: CGFloat, dockWidth: CGFloat, dockTopY: CGFloat) {
        // Always use the normal (walk) width for path math so enlarging the special window
        // doesn't compress dock travel distance mid-animation.
        let baseWidth = size.height * (videoWidth / videoHeight)
        currentTravelDistance = max(dockWidth - baseWidth, 0)
        if isIdleForPopover {
            let travelDistance = currentTravelDistance
            let x = dockX + travelDistance * positionProgress + currentFlipCompensation
            let bottomPadding = displayHeight * 0.15
            let y = dockTopY - bottomPadding + yOffset
            window.setFrameOrigin(NSPoint(x: x, y: y))
            updatePopoverPosition()
            updateThinkingBubble()
            return
        }

        let now = CACurrentMediaTime()

        if isPaused {
            if now >= pauseEndTime {
                beginMovement()
            } else {
                placeWindow(dockX: dockX, dockTopY: dockTopY)
                return
            }
        }

        if isPlayingSpecial {
            let elapsed = now - specialStartTime
            if !specialHasDashed && elapsed >= activeSpecialDashAt {
                specialHasDashed = true
                positionProgress = walkEndPos
            }
            if elapsed >= activeSpecialDuration {
                finishSpecial(restoreWalk: true)
                enterPause()
                placeWindow(dockX: dockX, dockTopY: dockTopY)
                updateThinkingBubble()
                return
            }
            placeWindow(dockX: dockX, dockTopY: dockTopY)
            updateThinkingBubble()
            return
        }

        if isWalking {
            let elapsed = now - walkStartTime
            let videoTime = min(elapsed, videoDuration)
            let walkNorm = elapsed >= videoDuration ? 1.0 : movementPosition(at: videoTime)

            // Drive dock X from planned progress endpoints (most reliable).
            // Pixel endpoints are kept for debugging / future multi-screen remaps.
            if abs(walkEndPos - walkStartPos) > 0.0001 {
                positionProgress = min(max(walkStartPos + (walkEndPos - walkStartPos) * walkNorm, 0), 1)
            } else {
                let travelDistance = max(currentTravelDistance, 1)
                let currentPixel = walkStartPixel + (walkEndPixel - walkStartPixel) * walkNorm
                positionProgress = min(max(currentPixel / travelDistance, 0), 1)
            }

            if elapsed >= videoDuration {
                walkEndPos = positionProgress
                enterPause()
                placeWindow(dockX: dockX, dockTopY: dockTopY)
                updateThinkingBubble()
                return
            }

            placeWindow(dockX: dockX, dockTopY: dockTopY)
        }

        updateThinkingBubble()
    }

    private func placeWindow(dockX: CGFloat, dockTopY: CGFloat) {
        let travelDistance = currentTravelDistance
        // Anchor feet using the normal (non-special) height so enlarging the special window
        // grows upward/outward without floating the character above the Dock.
        let baseHeight = size.height
        let baseWidth = baseHeight * (videoWidth / videoHeight)
        // Walk clips have ~15% empty padding under the feet (297/1920). Keep that constant
        // for both walk and special so soles stay on the dock line.
        let feetPadFraction: CGFloat = 297.0 / 1920.0
        let bottomPadding = baseHeight * feetPadFraction
        var y = dockTopY - bottomPadding + yOffset

        // If the special window is scaled up, feet would rise with the larger frame.
        // Nudge the window down by the extra scaled pad so feet stay dock-level.
        if isSpecialPresentationActive, activeSpecialSizeScale > 1.001 {
            let extraPad = baseHeight * feetPadFraction * (activeSpecialSizeScale - 1.0)
            y -= extraPad
        }

        // Base position (same as walk). When special window is wider, shift left so the
        // character stays centered under the same dock point — without breaking walk X.
        var x = dockX + travelDistance * positionProgress + currentFlipCompensation
        if displayWidth > baseWidth + 0.5 {
            x -= (displayWidth - baseWidth) / 2
        }
        window.setFrameOrigin(NSPoint(x: x, y: y))
    }
}
