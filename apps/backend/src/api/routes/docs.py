"""API documentation endpoints."""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, Response

router = APIRouter()


@router.get("/openapi.json", include_in_schema=False)
async def get_openapi_schema(request: Request):
    """获取 OpenAPI 规范文档，用于导入到 Hoppscotch 等 API 测试工具

    Returns:
        JSONResponse: OpenAPI 3.0 规范的 JSON 格式
    """
    # 获取 FastAPI 应用实例
    app = request.app
    return JSONResponse(content=app.openapi())


@router.get("/openapi.yaml", include_in_schema=False)
async def get_openapi_yaml(request: Request):
    """获取 YAML 格式的 OpenAPI 规范文档

    某些工具可能更喜欢 YAML 格式的 OpenAPI 文档

    Returns:
        Response: OpenAPI 3.0 规范的 YAML 格式
    """
    try:
        import yaml
    except ImportError:
        return JSONResponse(
            status_code=500, content={"error": "PyYAML not installed. Install with: pip install pyyaml"}
        )

    app = request.app
    openapi_dict = app.openapi()

    # 转换为 YAML 格式
    yaml_content = yaml.dump(openapi_dict, allow_unicode=True, sort_keys=False)

    return Response(
        content=yaml_content,
        media_type="application/x-yaml",
        headers={"Content-Disposition": "attachment; filename=openapi.yaml"},
    )
