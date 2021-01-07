apt update
{
  if [[ $(which python3) = "" ]]; then
    echo "Python 3 not found, installing with apt now..."
    apt install -y python3
    echo "Python 3 installed!"
  else
    echo "Python 3 installed!"
  fi

  if [[ $(which docker) = "" ]]; then
    echo "Docker not found, installing Docker for Ubuntu"
    apt remove -y docker docker-engine docker.io
    apt install -y \
      systemd \
      apt-transport-https \
      ca-certificates \
      curl \
      gnupg-agent \
      software-properties-common
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | apt-key add -
    add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu bionic stable"
    apt update
    apt-cache policy docker-ce
    apt install -y docker-ce
  else
    echo "Docker installed!"
  fi

  echo "Setup done, ready for you to install numerai-cli :)"
} || {
  echo "Setup script failed, please include the following along with the error if you report this:"
  lsb_release -a
}