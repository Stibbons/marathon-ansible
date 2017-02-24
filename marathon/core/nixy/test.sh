MARATHON_URL=`zk get /etc/cloud/marathon_uri |tail -n1`
rm -rf test
mkdir test
cp test.nixy.toml test/nixy.toml
ln nginx.tmpl test/
zk get --out test/forestscribe.crt /certs/forestscribe.crt
zk get --out test/forestscribe.key /certs/forestscribe.key
docker rm -f nixy; docker run -e MARATHON_LIST="[\"$MARATHON_URL\"]" --name nixy -it -p 7000:6000 -p 8443:443 -v `pwd`/test:/mnt/mesos/sandbox forestscribe/docker-nixy
