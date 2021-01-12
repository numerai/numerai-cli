
[CmdletBinding()] Param(
    $downloadsDir = "C:\Users\$env:UserName\Downloads",
    $installsDir = "C:\Program Files",
    $pythonVersion = "3.9.1",
    $pythonUrl = "https://www.python.org/ftp/python/$pythonVersion/python-$pythonVersion-amd64.exe",
    $pythonDownloadPath = "$downloadsDir\python-$pythonVersion-amd64-installer.exe",
    $pythonInstallDir = "$installsDir\Python$pythonVersion",
    $dockerUrl = "https://desktop.docker.com/win/stable/Docker%20Desktop%20Installer.exe",
    $dockerDownloadPath = "$downloadsDir\docker-installer.exe"
)
try {
    if (!(Get-Command python -errorAction SilentlyContinue)) {
        echo "python not found, installing..."

        New-Item -ItemType Directory -Force -Path $pythonInstallDir

        (New-Object Net.WebClient).DownloadFile($pythonUrl, $pythonDownloadPath)
        & $pythonDownloadPath /quiet InstallAllUsers=1 PrependPath=1 Include_test=0 TargetDir=$pythonInstallDir
        if ($LASTEXITCODE -ne 0) {
            throw "The python installer at '$pythonDownloadPath' exited with error code '$LASTEXITCODE'"
        }
        # Set the PATH environment variable for the entire machine (that is, for all users) to include the Python install dir
        [Environment]::SetEnvironmentVariable("PATH", "${env:path};${pythonInstallDir}", "Machine")
    }
    echo "python installed!"

    if (!(Get-Command docker -errorAction SilentlyContinue)) {
        echo "docker not found, installing..."
        
        (New-Object Net.WebClient).DownloadFile($dockerUrl, $dockerDownloadPath)
        & $dockerDownloadPath
    }
    echo "docker installed!"

    echo "Installation locations:"
    Get-Command python -errorAction SilentlyContinue
    Get-Command docker -errorAction SilentlyContinue

    echo "Setup done, ready for you to install numerai-cli :)"
}
Catch [Exception] {
    echo "Setup script failed, please include the following along with the error if you report this:"
    Write-Host $_.Exception | format-list -force
    Get-ComputerInfo
}

