import re
from pathlib import Path

FASTAPI_PATH = Path("/home/omdeep-borkar/projects/nikame/nikame/modules/api/fastapi.py")
content = FASTAPI_PATH.read_text()

# 1. Update flags in scaffold_files
flags_regex = r"has_db = any.*?has_messaging = .*?\]"
new_flags = """active_modules = [m.NAME for m in self.ctx.blueprint.modules]
        has_db = any(m in ["postgres", "timescaledb", "cockroachdb"] for m in active_modules)
        has_cache = any(m in ["dragonfly", "redis"] for m in active_modules)
        has_messaging = any(m in ["redpanda", "kafka"] for m in active_modules)
        has_storage = any(m in ["minio", "s3"] for m in active_modules)
        has_search = "elasticsearch" in active_modules
        has_neo4j = "neo4j" in active_modules
        has_clickhouse = "clickhouse" in active_modules
        has_vector = "qdrant" in active_modules
        has_temporal = "temporal" in active_modules
        has_ngrok = "ngrok" in active_modules
        has_smtp = "email" in self.ctx.features"""

content = re.sub(flags_regex, new_flags, content, flags=re.DOTALL)


# 2. Update imports in main.py
imports_regex = r"if has_messaging:.*?nikame_imports\.append\(\"from core\.messaging import kafka_service\"\)"
new_imports = """if has_messaging:
            nikame_imports.append("from core.messaging import kafka_service")
        if has_storage:
            nikame_imports.append("from core.storage import storage_client")
        if has_search:
            nikame_imports.append("from core.search import search_client")
        if has_neo4j:
            nikame_imports.append("from core.neo4j import neo4j_driver")
        if has_clickhouse:
            nikame_imports.append("from core.clickhouse import clickhouse_client")
        if has_vector:
            nikame_imports.append("from core.vector import vector_client")
        if has_temporal:
            nikame_imports.append("from core.temporal import temporal_client")
        if has_smtp:
            nikame_imports.append("from core.smtp import smtp_client")
        if has_ngrok:
            nikame_imports.append("from core.tunnel import start_tunnel")"""

content = re.sub(imports_regex, new_imports, content, flags=re.DOTALL)


# 3. Update lifespan checks
lifespan_regex = r"# 3\. Kafka/RedPanda connection check.*?yield"
new_lifespan_checks = """# 3. Kafka/RedPanda connection check
    if {has_messaging}:
        try:
            await kafka_service.start()
            logger.info("✓ Messaging service (Kafka) started")
        except Exception as e:
            logger.error(f"✗ Messaging service failed: {e}")

    if {has_ngrok} and settings.APP_ENV == "local":
        try:
            public_url = await start_tunnel()
            logger.info(f"✓ ngrok tunnel established: {public_url}")
        except Exception as e:
            logger.error(f"✗ ngrok tunnel failed: {e}")

    yield"""
content = re.sub(lifespan_regex, new_lifespan_checks, content, flags=re.DOTALL)


# 4. Update config settings
config_regex = r"KAFKA_BOOTSTRAP_SERVERS: str = \"\{self\.ctx\.all_env_vars\.get\('KAFKA_BOOTSTRAP_SERVERS', 'redpanda:9092'\)\}\""
new_config = """KAFKA_BOOTSTRAP_SERVERS: str = "{self.ctx.all_env_vars.get('KAFKA_BOOTSTRAP_SERVERS', 'redpanda:9092')}"
    MINIO_ENDPOINT: str = "{self.ctx.all_env_vars.get('MINIO_ENDPOINT', 'minio:9000')}"
    MINIO_ACCESS_KEY: str = "{self.ctx.all_env_vars.get('MINIO_ROOT_USER', 'minioadmin')}"
    MINIO_SECRET_KEY: str = "{self.ctx.all_env_vars.get('MINIO_ROOT_PASSWORD', 'minioadmin')}"
    ELASTICSEARCH_URL: str = "{self.ctx.all_env_vars.get('ELASTICSEARCH_URL', 'http://elasticsearch:9200')}"
    NEO4J_URI: str = "{self.ctx.all_env_vars.get('NEO4J_URI', 'bolt://neo4j:7687')}"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "{self.ctx.all_env_vars.get('NEO4J_PASSWORD', 'password')}"
    CLICKHOUSE_URL: str = "{self.ctx.all_env_vars.get('CLICKHOUSE_URL', 'clickhouse://default:@clickhouse:9000/default')}"
    QDRANT_URL: str = "http://qdrant:6333"
    TEMPORAL_TARGET: str = "temporal:7233"
    SMTP_HOST: str = "smtp.example.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = "user"
    SMTP_PASSWORD: str = "password"
    NGROK_AUTHTOKEN: str = "{self.ctx.all_env_vars.get('NGROK_AUTHTOKEN', '')}\""""
content = re.sub(config_regex, new_config, content)


# 5. Inject new core drivers
new_drivers = '''        # NEW DRIVERS
        if has_storage:
            storage_py = """\\"\\"\\"MinIO/S3 storage client wrapper.\\"\\"\\"
import aioboto3
from config import settings
import logging

logger = logging.getLogger(__name__)

class StorageClient:
    def __init__(self):
        self.session = aioboto3.Session()
        self.config = {
            "endpoint_url": f"http://{settings.MINIO_ENDPOINT}",
            "aws_access_key_id": settings.MINIO_ACCESS_KEY,
            "aws_secret_access_key": settings.MINIO_SECRET_KEY,
        }

    async def get_client(self):
        return self.session.client("s3", **self.config)

    async def upload_file(self, file_path: str, bucket: str, object_name: str):
        async with await self.get_client() as s3:
            await s3.upload_file(file_path, bucket, object_name)

    async def generate_presigned_url(self, bucket: str, object_name: str, exp: int = 3600):
        async with await self.get_client() as s3:
            return await s3.generate_presigned_url('get_object', Params={'Bucket': bucket, 'Key': object_name}, ExpiresIn=exp)

storage_client = StorageClient()
"""
            files.append(("app/core/storage.py", storage_py))

        if has_search:
            search_py = """\\"\\"\\"Elasticsearch async client wrapper.\\"\\"\\"
from elasticsearch import AsyncElasticsearch
from config import settings

search_client = AsyncElasticsearch(settings.ELASTICSEARCH_URL)
"""
            files.append(("app/core/search.py", search_py))

        if has_neo4j:
            neo4j_py = """\\"\\"\\"Neo4j async driver wrapper.\\"\\"\\"
from neo4j import AsyncGraphDatabase
from config import settings

neo4j_driver = AsyncGraphDatabase.driver(settings.NEO4J_URI, auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD))
"""
            files.append(("app/core/neo4j.py", neo4j_py))

        if has_clickhouse:
            clickhouse_py = """\\"\\"\\"ClickHouse async client.\\"\\"\\"
import aiochclient
import aiohttp
from config import settings

class ClickHouseClient:
    async def get_client(self):
        session = aiohttp.ClientSession()
        return aiochclient.ChClient(session, url=settings.CLICKHOUSE_URL)

clickhouse_client = ClickHouseClient()
"""
            files.append(("app/core/clickhouse.py", clickhouse_py))

        if has_vector:
            vector_py = """\\"\\"\\"Qdrant vector search client.\\"\\"\\"
from qdrant_client import AsyncQdrantClient
from config import settings

vector_client = AsyncQdrantClient(url=settings.QDRANT_URL)
"""
            files.append(("app/core/vector.py", vector_py))

        if has_temporal:
            temporal_py = """\\"\\"\\"Temporal workflow client.\\"\\"\\"
from temporalio.client import Client
from config import settings

class TemporalClient:
    async def connect(self):
        return await Client.connect(settings.TEMPORAL_TARGET)

temporal_client = TemporalClient()
"""
            files.append(("app/core/temporal.py", temporal_py))

        if has_smtp:
            smtp_py = """\\"\\"\\"SMTP email client.\\"\\"\\"
import aiosmtplib
from email.message import EmailMessage
from config import settings

class SMTPClient:
    async def send(self, to: str, subject: str, content: str):
        message = EmailMessage()
        message["From"] = settings.SMTP_USER
        message["To"] = to
        message["Subject"] = subject
        message.set_content(content)
        await aiosmtplib.send(
            message,
            hostname=settings.SMTP_HOST,
            port=settings.SMTP_PORT,
            username=settings.SMTP_USER,
            password=settings.SMTP_PASSWORD,
            use_tls=True
        )

smtp_client = SMTPClient()
"""
            files.append(("app/core/smtp.py", smtp_py))

        if has_ngrok:
            tunnel_py = """\\"\\"\\"Ngrok tunnel starter for local dev.\\"\\"\\"
from pyngrok import ngrok
from config import settings

async def start_tunnel():
    if settings.NGROK_AUTHTOKEN:
        ngrok.set_auth_token(settings.NGROK_AUTHTOKEN)
    tunnel = ngrok.connect(8000)
    return tunnel.public_url
"""
            files.append(("app/core/tunnel.py", tunnel_py))

        # 6.'''

# Inject before `# 6. app/routers/health.py`
inject_regex = r"# 6\. app/routers/health\.py"
content = re.sub(inject_regex, new_drivers, content)

FASTAPI_PATH.write_text(content)
print("Updated fastapi.py!")
