if [ $(which brew) = 'brew not installed' ]; then
  echo "Homebrew not found, installing now..."
  xcode-select --install
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install.sh)"
fi
echo "Homebrew installed! Updating..."
brew update

if [ $(which python3) = 'python3 not installed' ]; then
  echo "Python 3 not found, installing with homebrew now..."
  brew install python
fi
echo "Python 3 installed!"

if [ $(which docker) = 'docker not found' ]; then
  echo "Docker not found, downloading Docker Desktop now..."
  curl https://desktop.docker.com/mac/stable/Docker.dmg --output docker.dmg

  echo "Installing..."
  MOUNTDIR=$(echo `hdiutil mount docker.dmg | tail -1 | awk '{$1=$2=""; print $0}'` | xargs -0 echo)
  cp -R "${MOUNTDIR}/Docker.app" "${MOUNTDIR}/Applications/Docker.app"

  echo "Cleaning up..."
  hdiutil unmount "${MOUNTDIR}"
  rm docker.dmg

  echo "Starting Docker, please walk through the setup steps to finish the installation..."
  open ./Applications/Docker.app

  echo "Docker started! After finishing the install, run 'docker' in your terminal to ensure it's installed."
fi
echo "Docker installed!"

echo "Setup done :)"
