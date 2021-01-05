#!/bin/bash

if [[ $(which brew) = "brew not installed" ]]; then
  echo "Homebrew not found, installing now..."
  xcode-select --install
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install.sh)"
  echo "Homebrew installed! Updating..."
else
  echo "Homebrew installed! Updating..."
fi
brew update

if [[ $(which python3) = "python3 not installed" ]]; then
  echo "Python 3 not found, installing with homebrew now..."
  brew install python
  echo "Python 3 installed!"
else
  echo "Python 3 installed!"
fi

if [[ $(which numerai) = "numerai not found" ]]; then
  echo "Numerai CLI not found, installing with pip3..."
  pip3 install numerai-cli
  echo "Numerai CLI installed!"
else
  echo "Numerai CLI installed!"
fi

if [[ $(which docker) = "docker not found" ]]; then
  echo "Docker not found, downloading Docker Desktop now..."
  curl https://desktop.docker.com/mac/stable/Docker.dmg --output docker.dmg

  echo "Installing..."
  MOUNTDIR=$(echo `hdiutil mount docker.dmg | tail -1 | awk '{$1=$2=""; print $0}'` | xargs -0 echo)
  cp -R "${MOUNTDIR}/Docker.app" "${MOUNTDIR}/Applications/Docker.app"

  echo "Cleaning up..."
  hdiutil unmount "${MOUNTDIR}"
  rm docker.dmg

  echo "Starting Docker, please walk through the setup steps to finish the installation..."
  open /Applications/Docker.app

  echo "Docker started! After finishing the install, run 'docker' in your terminal to ensure it's installed."
else
  echo "Docker installed!"
fi

echo "Setup done :)"
