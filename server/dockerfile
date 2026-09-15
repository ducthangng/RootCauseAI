FROM pgvector/pgvector:pg16

# pgvector extension đã build sẵn trong image này, không cần compile thêm.
# Copy schema để tự động chạy khi container khởi tạo lần đầu (Postgres entrypoint
# chạy mọi *.sql trong /docker-entrypoint-initdb.d/ theo thứ tự tên file).
COPY schema.sql /docker-entrypoint-initdb.d/01-schema.sql