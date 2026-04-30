import json
import os
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from .services import call_fim_api
from .chat_service import call_chat_api
from .model_providers import get_all_models, get_available_providers, PROVIDER_CONFIG


def health(request):
    """Health check — returns provider status without exposing keys."""
    providers = {}
    for name, cfg in PROVIDER_CONFIG.items():
        key_set = bool(os.getenv(cfg["api_key_env"]))
        providers[name] = {"configured": key_set, "default_model": cfg["default_model"]}
    return JsonResponse({"status": "ok", "providers": providers})

CORS_ORIGIN = os.getenv("CORS_ALLOWED_ORIGIN", "*")


def cors_exempt(view_func):
    """CORS decorator — origin configurable via CORS_ALLOWED_ORIGIN env var."""

    def wrapped_view(request, *args, **kwargs):
        if request.method == "OPTIONS":
            response = HttpResponse()
            response["Access-Control-Allow-Origin"] = CORS_ORIGIN
            response["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
            response["Access-Control-Allow-Headers"] = "Content-Type"
            return response
        response = view_func(request, *args, **kwargs)
        response["Access-Control-Allow-Origin"] = CORS_ORIGIN
        response["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        response["Access-Control-Allow-Headers"] = "Content-Type"
        return response

    return wrapped_view


@csrf_exempt
@cors_exempt
def models(request):
    """获取支持的模型列表"""
    if request.method != "GET":
        return JsonResponse(
            {
                "success": False,
                "error_code": "INVALID_METHOD",
                "error": "只支持 GET 请求",
            },
            status=405,
        )

    return JsonResponse(
        {
            "success": True,
            "providers": get_available_providers(),
            "models": get_all_models(),
        }
    )


@csrf_exempt
@cors_exempt
def completion(request):
    """代码补全接口"""
    try:
        # 解析请求
        data = json.loads(request.body)

        # 验证必填参数
        required_fields = ["prompt", "suffix"]
        for field in required_fields:
            if field not in data:
                return JsonResponse(
                    {
                        "success": False,
                        "error_code": "INVALID_PARAMS",
                        "error": f"缺少必填参数: {field}",
                    },
                    status=400,
                )

        prompt = data["prompt"]
        suffix = data["suffix"]
        includes = data.get("includes", [])
        other_functions = data.get("other_functions", [])
        max_tokens = data.get("max_tokens", 100)

        # 调用DeepSeek FIM API
        suggestion = call_fim_api(prompt, suffix, includes, other_functions, max_tokens)

        # 构造响应
        return JsonResponse({"success": True, "suggestion": suggestion})

    except json.JSONDecodeError:
        return JsonResponse(
            {"success": False, "error_code": "INVALID_JSON", "error": "无效的JSON格式"},
            status=400,
        )
    except Exception as e:
        error_msg = str(e)
        error_code = "INTERNAL_ERROR"

        # 根据异常类型设置错误码
        if "timeout" in error_msg.lower():
            error_code = "API_TIMEOUT"
        elif "connection" in error_msg.lower():
            error_code = "API_CONNECTION_ERROR"
        elif "LLM API" in error_msg:
            error_code = "API_ERROR"

        return JsonResponse(
            {"success": False, "error_code": error_code, "error": error_msg}, status=500
        )


@csrf_exempt
@cors_exempt
def chat(request):
    """Chat 代码补全接口"""
    try:
        data = json.loads(request.body)

        if "context" not in data:
            return JsonResponse(
                {
                    "success": False,
                    "error_code": "INVALID_PARAMS",
                    "error": "缺少必填参数: context",
                },
                status=400,
            )

        context = data["context"]
        model = data.get("model")
        max_tokens = data.get("max_tokens", 1000)
        provider = data.get("provider", "zhipu")
        use_rag = data.get("use_rag", True)
        use_graph_rag = data.get("use_graph_rag", True)
        project_path = data.get("project_path", "")

        response = call_chat_api(
            context=context,
            model=model,
            max_tokens=max_tokens,
            provider=provider,
            use_rag=use_rag,
            use_graph_rag=use_graph_rag,
            project_path=project_path,
        )

        return JsonResponse({"success": True, "response": response})

    except json.JSONDecodeError:
        return JsonResponse(
            {"success": False, "error_code": "INVALID_JSON", "error": "无效的JSON格式"},
            status=400,
        )
    except ValueError as e:
        return JsonResponse(
            {"success": False, "error_code": "INVALID_PARAMS", "error": str(e)},
            status=400,
        )
    except Exception as e:
        error_msg = str(e)
        error_code = "INTERNAL_ERROR"

        if "timeout" in error_msg.lower():
            error_code = "API_TIMEOUT"
        elif "connection" in error_msg.lower():
            error_code = "API_CONNECTION_ERROR"
        elif "API" in error_msg:
            error_code = "API_ERROR"

        return JsonResponse(
            {"success": False, "error_code": error_code, "error": error_msg}, status=500
        )
