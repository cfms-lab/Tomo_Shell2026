# pics/ 그림 재생성 스크립트. 프로젝트 루트에서 실행할 것.
#   .\pics\regen_pics.ps1        -> 네 장 모두
#   .\pics\regen_pics.ps1 sh2    -> 특정 그림만 (sh1 | sh2 | sh3 | solid1)
# 카메라 설정값 설명은 pics/camera_settings.md 참조.
param(
    [ValidateSet('all', 'sh1', 'sh2', 'sh3', 'solid1')]
    [string]$Target = 'all'
)

$root = Split-Path -Parent $PSScriptRoot
Push-Location $root
try {
    $python = Join-Path $root '.venv\Scripts\python.exe'

    # 공통: headless
    $env:TOMO_NO_SHOW = '1'

    if ($Target -eq 'all' -or $Target -eq 'sh1') {
        $env:TOMO_PLOT3D_SAVE = 'pics/tomo_sh1.png'
        $env:TOMO_PLOT3D_DPI  = '100'
        & $python TSE_TomoSh1.py
        Remove-Item Env:TOMO_PLOT3D_SAVE, Env:TOMO_PLOT3D_DPI
    }

    if ($Target -eq 'all' -or $Target -eq 'solid1') {
        # solid mesh 예제: Bunny를 TSE_TomoSh1.py로 실행 (bShellMesh는 watertight 자동판정)
        $env:TOMO_MESH_FILE   = 'MeshData/Bunny_69k.stl'
        $env:TOMO_PLOT3D_SAVE = 'pics/tomo_solid1.png'
        $env:TOMO_PLOT3D_DPI  = '100'
        & $python TSE_TomoSh1.py
        Remove-Item Env:TOMO_MESH_FILE, Env:TOMO_PLOT3D_SAVE, Env:TOMO_PLOT3D_DPI
    }

    if ($Target -eq 'all' -or $Target -eq 'sh2') {
        $env:TOMO_SCREENSHOT       = 'pics/tomo_sh2.png'
        $env:TOMO_SCREENSHOT_W     = '1920'
        $env:TOMO_SCREENSHOT_H     = '768'
        $env:TOMO_CAMERA_VIEW      = 'front'
        $env:TOMO_CAMERA_DISTANCE  = '2.6'
        $env:TOMO_CAMERA_SHIFT     = '1.6'
        $env:TOMO_CAMERA_Z_OFFSET  = '0.04'
        $env:TOMO_GROUND_PLANE     = 'none'
        $env:TOMO_SSAA             = '3'
        & $python TSE_TomoSh2.py
        Remove-Item Env:TOMO_SCREENSHOT, Env:TOMO_SCREENSHOT_W, Env:TOMO_SCREENSHOT_H,
            Env:TOMO_CAMERA_VIEW, Env:TOMO_CAMERA_DISTANCE, Env:TOMO_CAMERA_SHIFT,
            Env:TOMO_CAMERA_Z_OFFSET, Env:TOMO_GROUND_PLANE, Env:TOMO_SSAA
        & $python pics/crop_margins.py pics/tomo_sh2.png
    }

    if ($Target -eq 'all' -or $Target -eq 'sh3') {
        $env:TOMO_SCREENSHOT       = 'pics/tomo_sh3.png'
        $env:TOMO_SCREENSHOT_W     = '1920'
        $env:TOMO_SCREENSHOT_H     = '768'
        $env:TOMO_CAMERA_VIEW      = 'front'
        $env:TOMO_CAMERA_DISTANCE  = '2.1'
        $env:TOMO_CAMERA_SHIFT     = '1.2'
        $env:TOMO_CAMERA_Z_OFFSET  = '0.02'
        $env:TOMO_GROUND_PLANE     = 'none'
        $env:TOMO_SSAA             = '3'
        & $python TSE_TomoSh3.py
        Remove-Item Env:TOMO_SCREENSHOT, Env:TOMO_SCREENSHOT_W, Env:TOMO_SCREENSHOT_H,
            Env:TOMO_CAMERA_VIEW, Env:TOMO_CAMERA_DISTANCE, Env:TOMO_CAMERA_SHIFT,
            Env:TOMO_CAMERA_Z_OFFSET, Env:TOMO_GROUND_PLANE, Env:TOMO_SSAA
        & $python pics/crop_margins.py pics/tomo_sh3.png
    }
}
finally {
    Remove-Item Env:TOMO_NO_SHOW -ErrorAction SilentlyContinue
    Pop-Location
}
