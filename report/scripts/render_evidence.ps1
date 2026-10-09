param([string]$Tag = '2026-10-09')

$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing
$reportDirectory = Split-Path -Parent $PSScriptRoot
$evidenceDirectory = Join-Path $reportDirectory 'evidence'
$imageDirectory = Join-Path $reportDirectory 'images'

function Read-Evidence([string]$Name) {
    $path = Join-Path $evidenceDirectory "$Tag-$Name.txt"
    return [System.IO.File]::ReadAllText($path)
}

function Write-OutputImage([string]$Name, [string]$Title, [string[]]$Lines) {
    $cleanLines = @($Lines | ForEach-Object {
        [regex]::Replace($_.Replace("`t", '    '), '[\x00-\x08\x0B-\x1F]', '')
    })
    $font = [System.Drawing.Font]::new('Cascadia Mono', 18, [System.Drawing.FontStyle]::Regular, [System.Drawing.GraphicsUnit]::Pixel)
    $scratch = [System.Drawing.Bitmap]::new(1, 1)
    $measure = [System.Drawing.Graphics]::FromImage($scratch)
    $width = 1080
    foreach ($line in $cleanLines) {
        $width = [Math]::Max($width, [int][Math]::Ceiling($measure.MeasureString($line, $font).Width) + 70)
    }
    $height = 112 + $cleanLines.Count * 27
    $bitmap = [System.Drawing.Bitmap]::new($width, $height)
    $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
    $graphics.TextRenderingHint = [System.Drawing.Text.TextRenderingHint]::ClearTypeGridFit
    $graphics.Clear([System.Drawing.Color]::FromArgb(18, 24, 34))
    $foreground = [System.Drawing.SolidBrush]::new([System.Drawing.Color]::FromArgb(223, 229, 237))
    $accent = [System.Drawing.SolidBrush]::new([System.Drawing.Color]::FromArgb(139, 206, 244))
    $success = [System.Drawing.SolidBrush]::new([System.Drawing.Color]::FromArgb(137, 212, 161))
    $graphics.DrawString($Title, $font, $accent, 28, 20)
    $graphics.DrawString("$Tag | Actual command output, rendered from report/evidence/", $font, $foreground, 28, 51)
    $y = 94
    foreach ($line in $cleanLines) {
        $brush = if ($line.StartsWith('PASS:')) { $success } else { $foreground }
        $graphics.DrawString($line, $font, $brush, 28, $y)
        $y += 27
    }
    $path = Join-Path $imageDirectory $Name
    $bitmap.Save($path, [System.Drawing.Imaging.ImageFormat]::Png)
    $graphics.Dispose()
    $bitmap.Dispose()
    $foreground.Dispose()
    $accent.Dispose()
    $success.Dispose()
    $measure.Dispose()
    $scratch.Dispose()
    $font.Dispose()
    Write-Output "Rendered $Name ($width x $height)"
}

$build = (Read-Evidence 'build') -split '\r?\n'
$compileStart = [Array]::IndexOf($build, '$ make clean')
$headerStart = [Array]::IndexOf($build, 'ELF Header:')
$buildLines = @($build[2..6]) + @('') + @($build[$compileStart..($headerStart - 2)])
$buildLines += @($build | Where-Object { $_ -match '^\s*(Class:|Machine:|Entry point address:)' })
$buildLines += @('') + @($build | Where-Object { $_ -match '^[0-9a-f]+ [A-Za-z] (kern_entry|kern_init|bootstack|bootstacktop|edata|end)$' })
Write-OutputImage '01-build-and-elf.png' 'Build, ELF header and kernel symbols' $buildLines

$boot = (Read-Evidence 'qemu') -split '\r?\n'
$bootLines = @($boot | Where-Object { $_ -match '^\$|^OpenSBI|^Platform Name|^Firmware Base|^Domain0 Next|^\(THU|^PASS:' })
Write-OutputImage '02-qemu-boot.png' 'QEMU / OpenSBI kernel handoff' $bootLines

$gdbText = Read-Evidence 'gdb'
$gdbText = ($gdbText -split 'GDB output:', 2)[1]
$gdbText = ($gdbText -split 'QEMU output after detach:', 2)[0]
$gdb = $gdbText -split '\r?\n'
$entryStart = -1
$sbiStart = -1
for ($i = 0; $i -lt $gdb.Count; $i++) {
    if ($gdb[$i] -match '^Breakpoint 2 at') { $entryStart = $i }
    if ($gdb[$i] -match '^Breakpoint 3 at') { $sbiStart = $i }
}
if ($entryStart -lt 0 -or $sbiStart -le $entryStart) { throw 'Expected GDB evidence blocks are missing' }
Write-OutputImage '03-gdb-kern-entry.png' 'Kernel entry: stack setup and tail call' @($gdb[$entryStart..($sbiStart - 1)])
Write-OutputImage '04-gdb-boot-chain.png' 'Reset -> OpenSBI -> kernel entry' @($gdb[1..($entryStart + 6)])

$layout = (Read-Evidence 'entry-layout') -split '\r?\n'
$layoutLines = @($layout | Where-Object { $_ -match '^Controlled|^Compiler|^CASE:|^Entry point|^kern_|^Kernel printed|^PASS:' })
Write-OutputImage '05-entry-layout.png' 'Link order: original layout and dedicated entry section' $layoutLines

$sbiLines = @($gdb[$sbiStart..($gdb.Count - 1)] | Where-Object { $_ -notmatch '^PASS:|^\[Inferior' })
Write-OutputImage '06-sbi-trap.png' 'SBI console request and machine-mode trap entry' $sbiLines
