from django.core.urlresolvers import reverse
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model, login
from django.utils.http import is_safe_url, urlencode
from django.views.generic import RedirectView

from . import discourse_sso
from .models import Nonce

MODEL_BACKEND_NAME = '{}.{}'.format(
    ModelBackend.__module__, ModelBackend.__name__)


class SSOViewMixin(object):
    DATA_REMAP = {
        'email': 'email',
        'moderator': 'is_staff',
        'admin': 'is_superuser',
        'username': 'name',
        'external_id': 'external_id',
    }

    def get_user(self, data):
        User = get_user_model()

        try:
            return User.objects.get(external_id=data['external_id']), False
        except User.DoesNotExist:
            pass

        try:
            obj = User.objects.get(name=data['name'])
            obj.external_id = data['external_id']
            obj.set_unusable_password()
            obj.save()
            return obj, False
        except User.DoesNotExist:
            pass

        obj, created = User.objects.get_or_create(
            external_id=data['external_id'], defaults=data)
        if created:
            obj.set_unusable_password()
            obj.save()

        return obj, created

    def discourse_data_to_oreuser_data(self, data):
        return {v: data[k] for k, v in self.DATA_REMAP.items()}

    def generate_sso_url(self, ret):
        if ret:
            ret = '?' + urlencode({'next': ret})
        else:
            ret = ''

        url = settings.DISCOURSE_SSO_URL
        if not url.endswith('?') and not url.endswith('&'):
            url += '&' if '?' in url else '?'
        return url + discourse_sso.generate_signed_query(self.request.build_absolute_uri(reverse('sso-return') + ret), settings.DISCOURSE_SSO_SECRET, settings.SECRET_KEY)

    def get_sso_data(self):
        sso, key = self.request.GET.get('sso'), self.request.GET.get('sig')
        sso_data = discourse_sso.unsigndata(
            sso, key, settings.DISCOURSE_SSO_SECRET)
        if not discourse_sso.checknonce(sso_data['nonce'], settings.SECRET_KEY):
            raise Exception('Nonce invalid')
        _, created = Nonce.objects.get_or_create(nonce=sso_data['nonce'])
        if not created:
            raise Exception('Nonce reused')
        return sso_data


class SSOBeginView(SSOViewMixin, RedirectView):
    permanent = False

    def get_redirect_url(self):
        ret = reverse('core-index')
        cret = self.request.GET.get('next', ret)
        if is_safe_url(cret):
            ret = cret
        return self.generate_sso_url(ret)


class SSOReturnView(SSOViewMixin, RedirectView):
    permanent = False

    def get_redirect_url(self):
        ret = reverse('core-index')
        cret = self.request.GET.get('next', ret)
        if is_safe_url(cret):
            return cret
        return ret

    def get(self, request, *args, **kwargs):
        try:
            sso_data = self.get_sso_data()
            user, is_new = self.get_user(
                self.discourse_data_to_oreuser_data(sso_data))
            user.backend = MODEL_BACKEND_NAME
            login(request, user)
            messages.success(
                request, "Welcome{}, {}!".format(' back' if not is_new else '', user.name))
        except Exception as ex:
            if settings.DEBUG:
                print(ex)
                raise
            messages.error(
                request, "Something went wrong whilst trying to verify your data. Try again in a few minutes, and inform a member of staff if you continue to receive errors.")
        return super().get(request, *args, **kwargs)
