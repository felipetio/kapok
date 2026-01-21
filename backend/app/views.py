from django.core.cache import cache
from django.db import connection
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_GET


def index(request):
    return HttpResponse("Hello, world.")


@require_GET
def health(request):
    """Health check endpoint for the application.

    Checks connectivity to PostgreSQL and Redis.
    Returns 200 if all services are healthy, 503 if any service is down.
    """
    checks = {
        "database": {"status": "healthy", "error": None},
        "cache": {"status": "healthy", "error": None},
    }

    # Check PostgreSQL
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception as e:
        checks["database"]["status"] = "unhealthy"
        checks["database"]["error"] = str(e)

    # Check Redis
    try:
        cache.set("health_check", "ok", timeout=1)
        if cache.get("health_check") != "ok":
            raise Exception("Cache read/write failed")
        cache.delete("health_check")
    except Exception as e:
        checks["cache"]["status"] = "unhealthy"
        checks["cache"]["error"] = str(e)

    # Determine overall status
    all_healthy = all(check["status"] == "healthy" for check in checks.values())

    health_data = {
        "status": "healthy" if all_healthy else "unhealthy",
        "checks": {
            name: check["status"] if check["error"] is None else {"status": check["status"], "error": check["error"]}
            for name, check in checks.items()
        },
    }

    status_code = 200 if all_healthy else 503
    return JsonResponse(health_data, status=status_code)
