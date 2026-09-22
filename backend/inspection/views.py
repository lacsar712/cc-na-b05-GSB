from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from inspection.models import Inspection, LimitChange, LimitSetting, RejectedReading
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
    limit = LimitSetting.current()
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
            if measured > limit.value:
                RejectedReading.objects.create(
                    aid_code=code,
                    measured_cd=measured,
                    limit_at_time=limit.value,
                    submitted_by=request.user.username,
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
@require_http_methods(["GET", "POST"])
def limit_view(request):
    setting = LimitSetting.current()
    error = ""
    if request.method == "POST":
        if not _can_write(request.user):
            return HttpResponseForbidden("仅巡检员可调整坎德拉上限")
        try:
            new_value = float(request.POST["value"])
        except (KeyError, ValueError):
            error = "请填有效的坎德拉数值"
        else:
            if new_value != setting.value:
                LimitChange.objects.create(
                    old_value=setting.value,
                    new_value=new_value,
                    changed_by=request.user.username,
                )
                setting.value = new_value
                setting.updated_by = request.user.username
                setting.save()
            return redirect("limit")
    history = LimitChange.objects.all()
    return render(
        request,
        "limit.html",
        {"setting": setting, "history": history, "error": error},
    )


@login_required
def rejected_view(request):
    rows = RejectedReading.objects.all()
    return render(request, "rejected.html", {"rows": rows})
