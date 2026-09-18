param([switch]$Stdio)

$ErrorActionPreference = "Stop"
[Console]::InputEncoding = [System.Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)

Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
Add-Type -AssemblyName WindowsBase
Add-Type -AssemblyName System.Drawing

Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;

public static class TitanNativeInput {
    [StructLayout(LayoutKind.Sequential)]
    public struct INPUT { public UInt32 type; public InputUnion U; }

    [StructLayout(LayoutKind.Explicit)]
    public struct InputUnion {
        [FieldOffset(0)] public MOUSEINPUT mi;
        [FieldOffset(0)] public KEYBDINPUT ki;
    }

    [StructLayout(LayoutKind.Sequential)]
    public struct MOUSEINPUT {
        public Int32 dx; public Int32 dy; public UInt32 mouseData;
        public UInt32 dwFlags; public UInt32 time; public UIntPtr dwExtraInfo;
    }

    [StructLayout(LayoutKind.Sequential)]
    public struct KEYBDINPUT {
        public UInt16 wVk; public UInt16 wScan; public UInt32 dwFlags;
        public UInt32 time; public UIntPtr dwExtraInfo;
    }

    [DllImport("user32.dll", SetLastError=true)]
    static extern UInt32 SendInput(UInt32 count, INPUT[] inputs, Int32 size);
    [DllImport("user32.dll")] public static extern bool SetCursorPos(Int32 x, Int32 y);
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hwnd);
    [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
    [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr hwnd, out RECT rect);
    [DllImport("user32.dll")] public static extern bool PrintWindow(IntPtr hwnd, IntPtr hdc, UInt32 flags);

    [StructLayout(LayoutKind.Sequential)]
    public struct RECT { public Int32 Left, Top, Right, Bottom; }

    const UInt32 INPUT_MOUSE = 0;
    const UInt32 INPUT_KEYBOARD = 1;
    const UInt32 MOUSEEVENTF_LEFTDOWN = 0x0002;
    const UInt32 MOUSEEVENTF_LEFTUP = 0x0004;
    const UInt32 MOUSEEVENTF_WHEEL = 0x0800;
    const UInt32 KEYEVENTF_KEYUP = 0x0002;
    const UInt32 KEYEVENTF_UNICODE = 0x0004;

    static void Send(INPUT[] inputs) {
        if (SendInput((UInt32)inputs.Length, inputs, Marshal.SizeOf(typeof(INPUT))) != inputs.Length)
            throw new System.ComponentModel.Win32Exception(Marshal.GetLastWin32Error());
    }

    public static void Click(Int32 x, Int32 y) {
        SetCursorPos(x, y);
        INPUT down = new INPUT { type = INPUT_MOUSE, U = new InputUnion { mi = new MOUSEINPUT { dwFlags = MOUSEEVENTF_LEFTDOWN } } };
        INPUT up = new INPUT { type = INPUT_MOUSE, U = new InputUnion { mi = new MOUSEINPUT { dwFlags = MOUSEEVENTF_LEFTUP } } };
        Send(new INPUT[] { down, up });
    }

    public static void Wheel(Int32 delta) {
        INPUT wheel = new INPUT { type = INPUT_MOUSE, U = new InputUnion { mi = new MOUSEINPUT { mouseData = unchecked((UInt32)delta), dwFlags = MOUSEEVENTF_WHEEL } } };
        Send(new INPUT[] { wheel });
    }

    public static void Key(UInt16 vk, bool down) {
        INPUT key = new INPUT { type = INPUT_KEYBOARD, U = new InputUnion { ki = new KEYBDINPUT { wVk = vk, dwFlags = down ? 0U : KEYEVENTF_KEYUP } } };
        Send(new INPUT[] { key });
    }

    public static void UnicodeText(string text) {
        foreach (char ch in text ?? "") {
            INPUT down = new INPUT { type = INPUT_KEYBOARD, U = new InputUnion { ki = new KEYBDINPUT { wScan = ch, dwFlags = KEYEVENTF_UNICODE } } };
            INPUT up = new INPUT { type = INPUT_KEYBOARD, U = new InputUnion { ki = new KEYBDINPUT { wScan = ch, dwFlags = KEYEVENTF_UNICODE | KEYEVENTF_KEYUP } } };
            Send(new INPUT[] { down, up });
        }
    }
}
'@

$script:Elements = @{}
$script:Walker = [System.Windows.Automation.TreeWalker]::ControlViewWalker

function Json-Line($Value) {
    $Value | ConvertTo-Json -Compress -Depth 14
}

function Fail($Reason, $Message, $Evidence = $null) {
    $out = [ordered]@{
        ok = $false
        kind = "failure"
        failure_reason = [string]$Reason
        message = [string]$Message
    }
    if ($null -ne $Evidence) { $out.evidence = $Evidence }
    return $out
}

function Get-Field($Object, $Name, $Default = $null) {
    if ($null -ne $Object -and $Object.PSObject.Properties.Name -contains $Name) {
        return $Object.$Name
    }
    return $Default
}

function Try-Value([scriptblock]$Read, $Default = $null) {
    try { return & $Read } catch { return $Default }
}

function Element-Id([System.Windows.Automation.AutomationElement]$Element) {
    $processId = Try-Value { $Element.Current.ProcessId } 0
    $rid = Try-Value { ($Element.GetRuntimeId() -join ".") } ""
    $hwnd = Try-Value { $Element.Current.NativeWindowHandle } 0
    $aid = Try-Value { $Element.Current.AutomationId } ""
    $raw = "$processId|$rid|$hwnd|$aid"
    $sha = [System.Security.Cryptography.SHA256]::Create()
    try {
        $bytes = [Text.Encoding]::UTF8.GetBytes($raw)
        $hex = [BitConverter]::ToString($sha.ComputeHash($bytes)).Replace("-", "").ToLowerInvariant()
        return "w_" + $hex.Substring(0, 20)
    } finally { $sha.Dispose() }
}

function Pattern([System.Windows.Automation.AutomationElement]$Element, $AutomationPattern) {
    $obj = $null
    try {
        if ($Element.TryGetCurrentPattern($AutomationPattern, [ref]$obj)) { return $obj }
    } catch {}
    return $null
}

function Element-Node([System.Windows.Automation.AutomationElement]$Element, [string]$ParentId) {
    $id = Element-Id $Element
    $script:Elements[$id] = $Element
    $control = Try-Value { $Element.Current.ControlType.ProgrammaticName } "ControlType.Unknown"
    $role = [string]$control -replace '^ControlType\.', ''
    $states = [System.Collections.Generic.List[string]]::new()
    if (Try-Value { $Element.Current.IsEnabled } $false) { $states.Add("enabled") } else { $states.Add("disabled") }
    if (Try-Value { $Element.Current.HasKeyboardFocus } $false) { $states.Add("focused") }
    if (Try-Value { $Element.Current.IsKeyboardFocusable } $false) { $states.Add("focusable") }
    if (Try-Value { $Element.Current.IsOffscreen } $false) { $states.Add("offscreen") }
    $isPassword = Try-Value { $Element.Current.IsPassword } $false
    if ($isPassword) { $states.Add("password") }

    $actions = [System.Collections.Generic.List[string]]::new()
    $invoke = Pattern $Element ([System.Windows.Automation.InvokePattern]::Pattern)
    if ($null -ne $invoke) { $actions.Add("invoke") }
    $valuePattern = Pattern $Element ([System.Windows.Automation.ValuePattern]::Pattern)
    if ($null -ne $valuePattern) { $actions.Add("set_value") }
    $toggle = Pattern $Element ([System.Windows.Automation.TogglePattern]::Pattern)
    if ($null -ne $toggle) { $actions.Add("toggle") }
    $expand = Pattern $Element ([System.Windows.Automation.ExpandCollapsePattern]::Pattern)
    if ($null -ne $expand) {
        $actions.Add("expand")
        $actions.Add("collapse")
    }
    $select = Pattern $Element ([System.Windows.Automation.SelectionItemPattern]::Pattern)
    if ($null -ne $select) { $actions.Add("select") }
    $scroll = Pattern $Element ([System.Windows.Automation.ScrollPattern]::Pattern)
    if ($null -ne $scroll) { $actions.Add("scroll") }
    if (Try-Value { $Element.Current.IsKeyboardFocusable } $false) { $actions.Add("focus") }
    $actions.Add("click")

    $value = ""
    if ($null -ne $valuePattern -and -not $isPassword) { $value = Try-Value { $valuePattern.Current.Value } "" }
    $rect = Try-Value { $Element.Current.BoundingRectangle } $null
    $bounds = $null
    if ($null -ne $rect -and -not $rect.IsEmpty) {
        $bounds = [ordered]@{
            x = [int][Math]::Round($rect.X)
            y = [int][Math]::Round($rect.Y)
            width = [int][Math]::Round($rect.Width)
            height = [int][Math]::Round($rect.Height)
        }
    }
    return [ordered]@{
        id = $id
        parent = $ParentId
        role = $role
        name = [string](Try-Value { $Element.Current.Name } "")
        automation_id = [string](Try-Value { $Element.Current.AutomationId } "")
        class_name = [string](Try-Value { $Element.Current.ClassName } "")
        help_text = [string](Try-Value { $Element.Current.HelpText } "")
        value = [string]$value
        process_id = [int](Try-Value { $Element.Current.ProcessId } 0)
        native_handle = [int](Try-Value { $Element.Current.NativeWindowHandle } 0)
        bounds = $bounds
        states = @($states)
        actions = @($actions | Sort-Object -Unique)
    }
}

function Snapshot($Request) {
    $maxNodes = [Math]::Max(1, [int](Get-Field $Request "max_nodes" 600))
    $maxDepth = [Math]::Max(0, [int](Get-Field $Request "max_depth" 8))
    $includeOffscreen = [bool](Get-Field $Request "include_offscreen" $false)
    $script:Elements = @{}
    $nodes = [System.Collections.Generic.List[object]]::new()
    $queue = [System.Collections.Generic.Queue[object]]::new()
    $root = [System.Windows.Automation.AutomationElement]::RootElement
    $child = $script:Walker.GetFirstChild($root)
    while ($null -ne $child) {
        $queue.Enqueue([pscustomobject]@{ element = $child; parent = ""; depth = 0 })
        $child = $script:Walker.GetNextSibling($child)
    }
    while ($queue.Count -gt 0 -and $nodes.Count -lt $maxNodes) {
        $item = $queue.Dequeue()
        $element = $item.element
        $offscreen = Try-Value { $element.Current.IsOffscreen } $false
        $node = Element-Node $element $item.parent
        if ($includeOffscreen -or -not $offscreen -or $item.depth -eq 0) { $nodes.Add($node) }
        if ($item.depth -ge $maxDepth) { continue }
        $next = Try-Value { $script:Walker.GetFirstChild($element) } $null
        while ($null -ne $next) {
            $queue.Enqueue([pscustomobject]@{ element = $next; parent = $node.id; depth = $item.depth + 1 })
            $next = Try-Value { $script:Walker.GetNextSibling($next) } $null
        }
    }
    $focused = Try-Value { [System.Windows.Automation.AutomationElement]::FocusedElement } $null
    $focusId = if ($null -ne $focused) { Element-Id $focused } else { "" }
    return [ordered]@{
        ok = $true
        kind = "full_snapshot"
        platform = "windows"
        captured_at = [DateTime]::UtcNow.ToString("o")
        focus_id = $focusId
        truncated = $queue.Count -gt 0
        coverage = [ordered]@{ returned = $nodes.Count; pending = $queue.Count; max_nodes = $maxNodes; max_depth = $maxDepth }
        nodes = @($nodes)
    }
}

function Need-Element($Action) {
    $id = [string](Get-Field $Action "id" "")
    if (-not $id -or -not $script:Elements.ContainsKey($id)) {
        throw [System.Collections.Generic.KeyNotFoundException]::new("element is absent or stale: $id")
    }
    return $script:Elements[$id]
}

function Key-Code([string]$Name) {
    $key = $Name.Trim().ToLowerInvariant()
    $named = @{
        "ctrl" = 0x11; "control" = 0x11; "shift" = 0x10; "alt" = 0x12; "win" = 0x5B
        "enter" = 0x0D; "return" = 0x0D; "tab" = 0x09; "escape" = 0x1B; "esc" = 0x1B
        "backspace" = 0x08; "delete" = 0x2E; "space" = 0x20
        "left" = 0x25; "up" = 0x26; "right" = 0x27; "down" = 0x28
        "home" = 0x24; "end" = 0x23; "pageup" = 0x21; "pagedown" = 0x22
        "f1" = 0x70; "f2" = 0x71; "f3" = 0x72; "f4" = 0x73; "f5" = 0x74; "f6" = 0x75
        "f7" = 0x76; "f8" = 0x77; "f9" = 0x78; "f10" = 0x79; "f11" = 0x7A; "f12" = 0x7B
    }
    if ($named.ContainsKey($key)) { return [uint16]$named[$key] }
    if ($key.Length -eq 1) { return [uint16][char]$key.ToUpperInvariant() }
    throw "unknown key: $Name"
}

function Click-Element([System.Windows.Automation.AutomationElement]$Element) {
    $point = New-Object System.Windows.Point
    $got = Try-Value { $Element.TryGetClickablePoint([ref]$point) } $false
    if (-not $got) {
        $rect = $Element.Current.BoundingRectangle
        if ($rect.IsEmpty) { throw "element has no clickable point or bounds" }
        $point = [System.Windows.Point]::new($rect.X + ($rect.Width / 2), $rect.Y + ($rect.Height / 2))
    }
    $hwnd = [int](Try-Value { $Element.Current.NativeWindowHandle } 0)
    if ($hwnd -ne 0) { [void][TitanNativeInput]::SetForegroundWindow([IntPtr]$hwnd) }
    [TitanNativeInput]::Click([int][Math]::Round($point.X), [int][Math]::Round($point.Y))
}

function Do-Action($Action) {
    $type = [string](Get-Field $Action "type" "")
    try {
        switch ($type.ToLowerInvariant()) {
            "invoke" {
                $element = Need-Element $Action
                $pattern = Pattern $element ([System.Windows.Automation.InvokePattern]::Pattern)
                if ($null -eq $pattern) { return Fail "PATTERN_UNAVAILABLE" "invoke pattern is unavailable" @{ id = $Action.id } }
                $pattern.Invoke()
            }
            "set_value" {
                $element = Need-Element $Action
                $pattern = Pattern $element ([System.Windows.Automation.ValuePattern]::Pattern)
                if ($null -eq $pattern) { return Fail "PATTERN_UNAVAILABLE" "value pattern is unavailable" @{ id = $Action.id } }
                $pattern.SetValue([string](Get-Field $Action "value" ""))
            }
            "toggle" {
                $element = Need-Element $Action
                $pattern = Pattern $element ([System.Windows.Automation.TogglePattern]::Pattern)
                if ($null -eq $pattern) { return Fail "PATTERN_UNAVAILABLE" "toggle pattern is unavailable" @{ id = $Action.id } }
                $pattern.Toggle()
            }
            "expand" {
                $element = Need-Element $Action
                $pattern = Pattern $element ([System.Windows.Automation.ExpandCollapsePattern]::Pattern)
                if ($null -eq $pattern) { return Fail "PATTERN_UNAVAILABLE" "expand pattern is unavailable" @{ id = $Action.id } }
                $pattern.Expand()
            }
            "collapse" {
                $element = Need-Element $Action
                $pattern = Pattern $element ([System.Windows.Automation.ExpandCollapsePattern]::Pattern)
                if ($null -eq $pattern) { return Fail "PATTERN_UNAVAILABLE" "collapse pattern is unavailable" @{ id = $Action.id } }
                $pattern.Collapse()
            }
            "select" {
                $element = Need-Element $Action
                $pattern = Pattern $element ([System.Windows.Automation.SelectionItemPattern]::Pattern)
                if ($null -eq $pattern) { return Fail "PATTERN_UNAVAILABLE" "selection pattern is unavailable" @{ id = $Action.id } }
                $pattern.Select()
            }
            "focus" { (Need-Element $Action).SetFocus() }
            "click" { Click-Element (Need-Element $Action) }
            "type_text" {
                $id = [string](Get-Field $Action "id" "")
                if ($id) { (Need-Element $Action).SetFocus() }
                [TitanNativeInput]::UnicodeText([string](Get-Field $Action "text" ""))
            }
            "key" {
                $parts = @(([string](Get-Field $Action "key" "")).Split("+") | Where-Object { $_.Trim() })
                if (-not $parts.Count) { throw "key action requires key" }
                $codes = @($parts | ForEach-Object { Key-Code $_ })
                foreach ($code in $codes) { [TitanNativeInput]::Key($code, $true) }
                [array]::Reverse($codes)
                foreach ($code in $codes) { [TitanNativeInput]::Key($code, $false) }
            }
            "scroll" {
                $delta = [int](Get-Field $Action "delta" -120)
                $id = [string](Get-Field $Action "id" "")
                $usedPattern = $false
                if ($id) {
                    $element = Need-Element $Action
                    $pattern = Pattern $element ([System.Windows.Automation.ScrollPattern]::Pattern)
                    if ($null -ne $pattern) {
                        $amount = if ($delta -lt 0) { [System.Windows.Automation.ScrollAmount]::SmallIncrement } else { [System.Windows.Automation.ScrollAmount]::SmallDecrement }
                        $pattern.Scroll([System.Windows.Automation.ScrollAmount]::NoAmount, $amount)
                        $usedPattern = $true
                    }
                }
                if (-not $usedPattern) { [TitanNativeInput]::Wheel($delta) }
            }
            "launch" {
                $file = [string](Get-Field $Action "file" "")
                if (-not $file) { throw "launch action requires file" }
                $arguments = @(Get-Field $Action "args" @())
                $startParameters = @{ FilePath = $file; PassThru = $true }
                if ($arguments.Count -gt 0) { $startParameters.ArgumentList = $arguments }
                $process = Start-Process @startParameters
                return [ordered]@{ ok = $true; kind = "action_outcome"; action = $type; process_id = $process.Id }
            }
            "wait" { Start-Sleep -Milliseconds ([Math]::Max(0, [int](Get-Field $Action "milliseconds" 250))) }
            "done" { return [ordered]@{ ok = $true; kind = "done"; message = [string](Get-Field $Action "message" "") } }
            default { return Fail "UNSUPPORTED_ACTION" "backend does not implement action: $type" @{ action = $type } }
        }
        return [ordered]@{ ok = $true; kind = "action_outcome"; action = $type; id = [string](Get-Field $Action "id" "") }
    } catch [System.Collections.Generic.KeyNotFoundException] {
        return Fail "ELEMENT_STALE" $_.Exception.Message @{ id = [string](Get-Field $Action "id" "") }
    } catch {
        return Fail "ACTION_FAILED" $_.Exception.Message @{ action = $type; id = [string](Get-Field $Action "id" "") }
    }
}

function Capture($Request) {
    try {
        $id = [string](Get-Field $Request "id" "")
        $hwnd = [IntPtr]::Zero
        if ($id) {
            $element = Need-Element $Request
            $hwnd = [IntPtr][int](Try-Value { $element.Current.NativeWindowHandle } 0)
        }
        if ($hwnd -eq [IntPtr]::Zero) { $hwnd = [TitanNativeInput]::GetForegroundWindow() }
        if ($hwnd -eq [IntPtr]::Zero) { return Fail "WINDOW_MISS" "no target or foreground window" }
        $rect = New-Object TitanNativeInput+RECT
        if (-not [TitanNativeInput]::GetWindowRect($hwnd, [ref]$rect)) { return Fail "WINDOW_MISS" "GetWindowRect failed" }
        $width = [Math]::Max(1, $rect.Right - $rect.Left)
        $height = [Math]::Max(1, $rect.Bottom - $rect.Top)
        $path = [string](Get-Field $Request "path" "")
        if (-not $path) { $path = Join-Path ([IO.Path]::GetTempPath()) ("titan-hands-" + [Guid]::NewGuid().ToString("n") + ".png") }
        $path = [IO.Path]::GetFullPath($path)
        $parent = Split-Path -Parent $path
        if ($parent) { [IO.Directory]::CreateDirectory($parent) | Out-Null }
        $bitmap = [Drawing.Bitmap]::new($width, $height, [Drawing.Imaging.PixelFormat]::Format32bppArgb)
        $graphics = [Drawing.Graphics]::FromImage($bitmap)
        $method = "PrintWindow"
        try {
            $hdc = $graphics.GetHdc()
            try { $printed = [TitanNativeInput]::PrintWindow($hwnd, $hdc, 2) } finally { $graphics.ReleaseHdc($hdc) }
            if (-not $printed) {
                $method = "CopyFromScreen"
                $graphics.CopyFromScreen($rect.Left, $rect.Top, 0, 0, [Drawing.Size]::new($width, $height))
            }
            $bitmap.Save($path, [Drawing.Imaging.ImageFormat]::Png)
        } finally {
            $graphics.Dispose()
            $bitmap.Dispose()
        }
        $hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $path).Hash.ToLowerInvariant()
        return [ordered]@{
            ok = $true; kind = "pixel_capture"; pixel_ref = $path; sha256 = $hash
            width = $width; height = $height; method = $method; captured_at = [DateTime]::UtcNow.ToString("o")
        }
    } catch [System.Collections.Generic.KeyNotFoundException] {
        return Fail "ELEMENT_STALE" $_.Exception.Message
    } catch {
        return Fail "CAPTURE_FAILED" $_.Exception.Message
    }
}

function Dispatch($Request) {
    $op = [string](Get-Field $Request "op" "")
    switch ($op.ToLowerInvariant()) {
        "capabilities" {
            return [ordered]@{
                ok = $true
                backend = "Windows UI Automation + SendInput + PrintWindow"
                observation = "semantic-full-snapshot"
                pixels = "on-demand-only"
                actions = @("invoke", "set_value", "toggle", "expand", "collapse", "select", "focus", "click", "type_text", "key", "scroll", "launch", "wait", "done")
                capture = @("PrintWindow", "CopyFromScreen fallback")
            }
        }
        "snapshot" { return Snapshot $Request }
        "action" { return Do-Action (Get-Field $Request "action" $null) }
        "capture" { return Capture $Request }
        "shutdown" { return [ordered]@{ ok = $true; kind = "shutdown" } }
        default { return Fail "UNKNOWN_OPERATION" "unknown backend operation: $op" }
    }
}

if (-not $Stdio) {
    Json-Line (Dispatch ([pscustomobject]@{ op = "capabilities" }))
    exit 0
}

while ($null -ne ($line = [Console]::In.ReadLine())) {
    if (-not $line.Trim()) { continue }
    try {
        $request = $line | ConvertFrom-Json
        $response = Dispatch $request
    } catch {
        $response = Fail "INVALID_JSON" $_.Exception.Message
    }
    [Console]::Out.WriteLine((Json-Line $response))
    [Console]::Out.Flush()
    if ([string](Get-Field $request "op" "") -eq "shutdown") { break }
}
