from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from inspection.models import CandelaLimit, Inspection, LimitHistory, RejectedLight
from inspection.rules import judge


def _can_write(user) -> bool:
    return user.groups.filter(name="inspector").exists()


def health(_request):
    from django.http import JsonResponse

    return JsonResponse({"status": "ok", "service": "nav-aid-inspection"})


@require_http_methods(["GET", "POST"])
def login_view(request):
    from django.contrib.auth import authenticate, login

    error = ""
    if request.method == "POST":
        user = authenticate(
            request,
            username=request.POST.get("username", "").strip(),
            password=request.POST.get("password", ""),
        )
        if user is None:
            error = "用户名或密码错误"
        else:
            login(request, user)
            return redirect("list")
    return render(request, "login.html", {"error": error})


def logout_view(request):
    from django.contrib.auth import logout

    logout(request)
    return redirect("login")


@login_required
def list_view(request):
    rows = Inspection.objects.all()
    return render(request, "list.html", {"rows": rows, "can_write": _can_write(request.user)})


@login_required
def detail_view(request, pk):
    row = get_object_or_404(Inspection, pk=pk)
    return render(request, "detail.html", {"row": row})


@login_required
@require_http_methods(["GET", "POST"])
def create_view(request):
    if not _can_write(request.user):
        return HttpResponseForbidden("仅巡检员可登记灯光巡检")
    error = ""
    limit = CandelaLimit.current()
    if request.method == "POST":
        try:
            measured = float(request.POST["measured_cd"])
            required = float(request.POST["required_cd"])
            bearing = float(request.POST["bearing_error_deg"])
            code = request.POST["aid_code"].strip()
            if not code:
                raise ValueError("empty")
        except (KeyError, ValueError):
            error = "请填编号和三项数值"
        else:
            # 以拒绝瞬间的上限为快照；上限以后再改也不会覆盖这条记录。
            if measured > limit.value:
                RejectedLight.objects.create(
                    aid_code=code,
                    measured_cd=measured,
                    limit_at_rejection=limit.value,
                    rejected_by=request.user.username,
                )
                messages.error(
                    request,
                    f"{code} 所填亮度 {measured:g} 超过上限 {limit.value:g}，已拒绝并记入被拒灯光页",
                )
                return redirect("rejected")
            verdict, note = judge(measured, required, bearing)
            row = Inspection.objects.create(
                aid_code=code,
                measured_cd=measured,
                required_cd=required,
                bearing_error_deg=bearing,
                verdict=verdict,
                note=note,
                created_by=request.user.username,
            )
            return redirect("detail", pk=row.pk)
    return render(request, "form.html", {"error": error, "limit": limit})


@login_required
def rejected_view(request):
    rows = RejectedLight.objects.all()
    return render(request, "rejected.html", {"rows": rows})


@login_required
@require_http_methods(["GET", "POST"])
def limit_view(request):
    if request.method == "POST" and not _can_write(request.user):
        return HttpResponseForbidden("仅持灯账号可修改坎德拉上限")
    limit = CandelaLimit.current()
    error = ""
    if request.method == "POST":
        try:
            new_value = float(request.POST["value"])
        except (KeyError, ValueError):
            error = "请填写数值上限"
        else:
            if new_value < 0:
                error = "上限不能为负"
            elif new_value == limit.value:
                error = "新上限与当前上限相同，未改动"
            else:
                CandelaLimit.change(new_value, request.user.username)
                messages.success(
                    request,
                    f"上限已由 {limit.value:g} 调整为 {new_value:g}，履历已记录",
                )
                return redirect("limit")
    history = LimitHistory.objects.all()
    return render(
        request,
        "limit.html",
        {"limit": limit, "history": history, "error": error},
    )
