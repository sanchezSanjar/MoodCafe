# Draws the Mood Cafe logo (smiling coffee cup) and writes assets\moodcafe.ico (16-256 px PNG entries).
Add-Type -AssemblyName System.Drawing

$root = Split-Path -Parent $PSScriptRoot
New-Item -ItemType Directory -Force (Join-Path $root "assets") | Out-Null
$icoPath = Join-Path $root "assets\moodcafe.ico"

$images = @()
foreach ($size in 16, 24, 32, 48, 64, 128, 256) {
    $s = [single]$size
    $bmp = New-Object System.Drawing.Bitmap $size, $size
    $g = [System.Drawing.Graphics]::FromImage($bmp)
    $g.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
    $g.Clear([System.Drawing.Color]::Transparent)
    $coffee = [System.Drawing.ColorTranslator]::FromHtml("#6f4e37")
    $foam = [System.Drawing.ColorTranslator]::FromHtml("#efe3d3")
    $g.FillEllipse((New-Object System.Drawing.SolidBrush $coffee), $s * 0.03, $s * 0.03, $s * 0.94, $s * 0.94)

    # Cup body and handle
    $cup = New-Object System.Drawing.Drawing2D.GraphicsPath
    $cup.AddLine($s * 0.24, $s * 0.36, $s * 0.70, $s * 0.36)
    $cup.AddLine($s * 0.70, $s * 0.36, $s * 0.64, $s * 0.74)
    $cup.AddLine($s * 0.64, $s * 0.74, $s * 0.30, $s * 0.74)
    $cup.CloseFigure()
    $g.FillPath((New-Object System.Drawing.SolidBrush $foam), $cup)
    $pen = New-Object System.Drawing.Pen $foam, ([Math]::Max(1, $s * 0.06))
    $g.DrawArc($pen, $s * 0.60, $s * 0.42, $s * 0.20, $s * 0.20, -90, 180)

    # Smile on the cup
    if ($size -ge 24) {
        $smile = New-Object System.Drawing.Pen $coffee, ([Math]::Max(1, $s * 0.045))
        $g.DrawArc($smile, $s * 0.36, $s * 0.42, $s * 0.22, $s * 0.18, 20, 140)
        $eye = New-Object System.Drawing.SolidBrush $coffee
        $g.FillEllipse($eye, $s * 0.38, $s * 0.43, $s * 0.05, $s * 0.05)
        $g.FillEllipse($eye, $s * 0.51, $s * 0.43, $s * 0.05, $s * 0.05)
    }
    $g.Dispose()

    $stream = New-Object System.IO.MemoryStream
    $bmp.Save($stream, [System.Drawing.Imaging.ImageFormat]::Png)
    $images += , @($size, $stream.ToArray())
    $bmp.Dispose()
}

$out = New-Object System.IO.MemoryStream
$w = New-Object System.IO.BinaryWriter $out
$w.Write([UInt16]0); $w.Write([UInt16]1); $w.Write([UInt16]$images.Count)
$offset = 6 + 16 * $images.Count
foreach ($img in $images) {
    $dim = if ($img[0] -ge 256) { 0 } else { $img[0] }
    $w.Write([byte]$dim); $w.Write([byte]$dim); $w.Write([byte]0); $w.Write([byte]0)
    $w.Write([UInt16]1); $w.Write([UInt16]32)
    $w.Write([UInt32]$img[1].Length); $w.Write([UInt32]$offset)
    $offset += $img[1].Length
}
foreach ($img in $images) { $w.Write($img[1]) }
$w.Flush()
[System.IO.File]::WriteAllBytes($icoPath, $out.ToArray())
Write-Output "Icon written: $icoPath"
