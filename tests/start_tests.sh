#! /bin/bash
cd /server
touch controller.log
touch controller.debug
python3 -u controller.py 8088 2>&1 >controller.log &
PID=$!

cd /tests
./wait-for-it.sh -h localhost -p 8088
echo "Starting tests"
SYSEXIT=0
while IFS= read -r line
do
  echo "$line"
  python3 -u test.py $line | tee -a test.log
  if [ $? -ne 0 ]; then
    SYSEXIT=1
  fi
done < tests.conf

kill $PID

cat /server/controller.log /server/controller.debug
cat test.log

exit ${SYSEXIT}
