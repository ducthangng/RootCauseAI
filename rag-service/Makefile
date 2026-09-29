build:
	docker build -f arm.dockerfile -t rootcause:latest .

uv-export-pkg:
	uv export --no-hashes --no-dev --no-emit-project -o requirements.txt

clean-up-docker:
# 	xoá build cache (thủ phạm chính sau các lần build 14GB)
	docker builder prune -a -f          
# xoá image dangling (<none>)
	docker image prune -f               
# xoá container đã stop
	docker container prune -f