docker build . -f Dockerfile_app -t harbor.nuvem.online/glpi-automator/app:v1.0.1
docker build . -f Dockerfile_flower -t harbor.nuvem.online/glpi-automator/flower:v1.0.1
docker build . -f Dockerfile_worker -t harbor.nuvem.online/glpi-automator/worker:v1.0.1

docker push harbor.nuvem.online/glpi-automator/app:v1.0.1
docker push harbor.nuvem.online/glpi-automator/flower:v1.0.1
docker push harbor.nuvem.online/glpi-automator/worker:v1.0.1