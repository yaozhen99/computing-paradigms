# Resize image to approximately 200KB
param(
    [string]$SourceImage = "D:\Netdef\netdef.png",
    [string]$OutputImage = "D:\Netdef\FirewallScripts\tests\netdef-resized.png",
    [int]$TargetSizeKB = 200
)

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Netdef Image Resizer" -ForegroundColor White
Write-Host "============================================" -ForegroundColor Cyan

# Check if source image exists
if (-not (Test-Path $SourceImage)) {
    Write-Host "[ERROR] Source image not found: $SourceImage" -ForegroundColor Red
    exit 1
}

# Check if .NET System.Drawing is available
try {
    Add-Type -AssemblyName System.Drawing -ErrorAction Stop
} catch {
    Write-Host "[ERROR] System.Drawing assembly not available" -ForegroundColor Red
    exit 1
}

# Function to get image size in KB
function Get-ImageSizeKB {
    param([string]$Path)
    $size = (Get-Item $Path).Length / 1024
    return [math]::Round($size, 2)
}

# Function to resize image
function Resize-Image {
    param(
        [string]$SourcePath,
        [string]$OutputPath,
        [int]$Width,
        [int]$Height
    )
    
    try {
        $sourceImage = [System.Drawing.Image]::FromFile($SourcePath)
        $resizedImage = New-Object System.Drawing.Bitmap($Width, $Height)
        $graphics = [System.Drawing.Graphics]::FromImage($resizedImage)
        $graphics.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
        $graphics.DrawImage($sourceImage, 0, 0, $Width, $Height)
        $resizedImage.Save($OutputPath, [System.Drawing.Imaging.ImageFormat]::Png)
        $sourceImage.Dispose()
        $resizedImage.Dispose()
        $graphics.Dispose()
        return $true
    } catch {
        Write-Host "[ERROR] Failed to resize image: $_" -ForegroundColor Red
        return $false
    }
}

# Get original image dimensions
$originalImage = [System.Drawing.Image]::FromFile($SourceImage)
$originalWidth = $originalImage.Width
$originalHeight = $originalImage.Height
$originalImage.Dispose()

Write-Host "[INFO] Original image: $SourceImage" -ForegroundColor Green
Write-Host "[INFO] Original dimensions: $originalWidth x $originalHeight" -ForegroundColor Green
Write-Host "[INFO] Target size: $TargetSizeKB KB" -ForegroundColor Green

# Calculate target dimensions (maintain aspect ratio)
$aspectRatio = $originalWidth / $originalHeight
$targetWidth = 400
$targetHeight = [math]::Round($targetWidth / $aspectRatio)

Write-Host "[INFO] Resizing to: $targetWidth x $targetHeight" -ForegroundColor Cyan

# Resize image
if (Resize-Image -SourcePath $SourceImage -OutputPath $OutputImage -Width $targetWidth -Height $targetHeight) {
    $currentSize = Get-ImageSizeKB $OutputImage
    Write-Host "[INFO] Resized image saved to: $OutputImage" -ForegroundColor Green
    Write-Host "[INFO] Current size: $currentSize KB" -ForegroundColor Green
    
    # If size is still too large, try lower quality
    if ($currentSize -gt $TargetSizeKB) {
        Write-Host "[INFO] Size too large, trying lower quality..." -ForegroundColor Yellow
        
        # Try smaller dimensions
        $targetWidth = 300
        $targetHeight = [math]::Round($targetWidth / $aspectRatio)
        Write-Host "[INFO] Resizing to: $targetWidth x $targetHeight" -ForegroundColor Cyan
        
        if (Resize-Image -SourcePath $SourceImage -OutputPath $OutputImage -Width $targetWidth -Height $targetHeight) {
            $currentSize = Get-ImageSizeKB $OutputImage
            Write-Host "[INFO] New size: $currentSize KB" -ForegroundColor Green
        }
        
        # If still too large, try even smaller
        if ($currentSize -gt $TargetSizeKB) {
            $targetWidth = 200
            $targetHeight = [math]::Round($targetWidth / $aspectRatio)
            Write-Host "[INFO] Resizing to: $targetWidth x $targetHeight" -ForegroundColor Cyan
            
            if (Resize-Image -SourcePath $SourceImage -OutputPath $OutputImage -Width $targetWidth -Height $targetHeight) {
                $currentSize = Get-ImageSizeKB $OutputImage
                Write-Host "[INFO] New size: $currentSize KB" -ForegroundColor Green
            }
        }
    }
    
    # Final check
    $finalSize = Get-ImageSizeKB $OutputImage
    if ($finalSize -le $TargetSizeKB) {
        Write-Host "[SUCCESS] Image resized to $finalSize KB (target: $TargetSizeKB KB)" -ForegroundColor Green
    } else {
        Write-Host "[WARNING] Image size ($finalSize KB) is still larger than target ($TargetSizeKB KB)" -ForegroundColor Yellow
    }
} else {
    Write-Host "[ERROR] Failed to resize image" -ForegroundColor Red
    exit 1
}

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Image resizing complete!" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Cyan
