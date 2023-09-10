from django.shortcuts import render,redirect

from django.views import View


from users.models import CustomUser

from django.contrib.auth.mixins import LoginRequiredMixin
from django.conf import settings
from django.urls import reverse_lazy

import stripe
stripe.api_key  = settings.STRIPE_API_KEY

class IndexView(LoginRequiredMixin,View):
    def get(self, request, *args, **kwargs):
        return render(request,"bbs/index.html")

index   = IndexView.as_view()

class CheckoutView(LoginRequiredMixin,View):

    def post(self, request, *args, **kwargs):

        # セッションを作る
        checkout_session = stripe.checkout.Session.create(
            line_items=[
                {
                    'price': settings.STRIPE_PRICE_ID,
                    'quantity': 1,
                },
            ],
            payment_method_types=['card'],
            mode='subscription',
            success_url=request.build_absolute_uri(reverse_lazy("bbs:success")) + '?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=request.build_absolute_uri(reverse_lazy("bbs:index")),
        )

        print( checkout_session["id"] )

        return redirect(checkout_session.url)

checkout    = CheckoutView.as_view()


class SuccessView(LoginRequiredMixin,View):
    def get(self, request, *args, **kwargs):

        # パラメータにセッションIDがあるかチェック
        if "session_id" not in request.GET:
            print("セッションIDがありません。")
            return redirect("bbs:index")

        # そのセッションIDは有効であるかチェック。
        try:
            checkout_session_id = request.GET['session_id']
            checkout_session    = stripe.checkout.Session.retrieve(checkout_session_id)
        except:
            print( "このセッションIDは無効です。")
            return redirect("bbs:index")

        
        #TODO: statusをチェックする。未払であれば拒否する。
        if checkout_session["status"] != "paid":
            print("未払い")
            return redirect("bbs:index")

        print("支払い済み")


        # 有効であれば、セッションIDからカスタマーIDを取得。ユーザーモデルへカスタマーIDを記録する。
        user            = CustomUser.objects.filter(id=request.user.id).first()
        user.customer   = checkout_session["customer"]
        user.save()

        print("有料会員登録しました！")

        return redirect("bbs:index")

success     = SuccessView.as_view()



# サブスクリプションの操作関係
class PortalView(LoginRequiredMixin,View):
    def get(self, request, *args, **kwargs):

        if not request.user.customer:
            print( "有料会員登録されていません")
            return redirect("bbs:index")

        # ユーザーモデルに記録しているカスタマーIDを使って、ポータルサイトへリダイレクト
        portalSession   = stripe.billing_portal.Session.create(
            customer    = request.user.customer,
            return_url  = request.build_absolute_uri(reverse_lazy("bbs:index")),
            )

        return redirect(portalSession.url)

portal      = PortalView.as_view()
