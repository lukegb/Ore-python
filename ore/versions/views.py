from ore.core.models import Namespace
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import DetailView, FormView, TemplateView, UpdateView, DeleteView
from django.views.generic.detail import SingleObjectMixin
from django.core.urlresolvers import reverse
from django.http import Http404
from ore.projects.models import Project, Channel
from ore.projects.views import ProjectNavbarMixin
from ore.core.views import RequiresPermissionMixin, MultiFormMixin
from ore.versions.forms import NewVersionForm, NewChannelForm, ChannelDeleteForm, EditVersionForm, NewFileForm
from ore.versions.models import Version, File


class ProjectsVersionsListView(ProjectNavbarMixin, DetailView):

    model = Project
    slug_field = 'name'
    slug_url_kwarg = 'project'

    template_name = 'versions/list.html'
    context_object_name = 'proj'
    active_project_tab = 'versions'

    def get_queryset(self):
        return Project.objects.as_user(self.request.user).filter(namespace__name=self.kwargs['namespace'])


class VersionsNewView(RequiresPermissionMixin, TemplateView):

    template_name = 'versions/new.html'

    permissions = ['project.manage', 'version.create', 'file.create']

    def get_project(self):
        return get_object_or_404(Project.objects.as_user(self.request.user), name=self.kwargs['project'], namespace__name=self.kwargs['namespace'])

    def get_context_data(self, **kwargs):
        data = super(VersionsNewView, self).get_context_data(**kwargs)
        data.update({
            'proj': self.get_project()
        })
        return data

    def get_form(self):
        project = self.get_project()
        if self.request.method == 'GET':
            return NewVersionForm(project=project)
        return NewVersionForm(self.request.POST, self.request.FILES, project=project)

    def get(self, request, *args, **kwargs):
        return self.render_to_response(self.get_context_data(form=self.get_form()))

    def post(self, request, *args, **kwargs):
        form = self.get_form()
        if form.is_valid():
            # create a new version
            project = self.get_project()
            channel = project.channel_set.get(id=form.cleaned_data['channel'])
            version = Version(
                name=form.cleaned_data['plugin'].data['version'],
                project=project,
                channel=channel,
            )
            file = File(
                project=project,
                version=version,
                file=form.cleaned_data['file'],
                file_name=form.cleaned_data['file_name'],
                file_extension=form.cleaned_data['file_extension'],
                file_size=form.cleaned_data['file_size'],
                plugin_id=form.cleaned_data['plugin'].data['id'],
                plugin_dependencies=form.cleaned_data['plugin'].json_dependencies,
            )
            version.save()
            file.version = version
            file.save()
            return redirect(reverse('versions-manage', kwargs={'namespace': self.kwargs['namespace'], 'project': self.kwargs['project'], 'version': version.name}))

        return self.render_to_response(self.get_context_data(form=form))


class VersionsDetailView(ProjectNavbarMixin, DetailView):

    model = Version
    slug_field = 'name'
    slug_url_kwarg = 'version'
    template_name = 'versions/detail.html'
    active_project_tab = 'versions'

    def get_queryset(self):
        return Version.objects.as_user(self.request.user).filter(project__namespace__name=self.kwargs['namespace'], project__name=self.kwargs['project']).select_related('project')

    def get_namespace(self):
        if not hasattr(self, "_namespace"):
            self._namespace = get_object_or_404(Namespace.objects.as_user(
                self.request.user).select_subclasses(), name=self.kwargs['namespace'])
            return self._namespace
        else:
            return self._namespace

    def get_context_data(self, **kwargs):
        context = super(VersionsDetailView, self).get_context_data(**kwargs)
        context['namespace'] = self.get_namespace()
        context['proj'] = context['version'].project
        return context


class VersionsManageMixin(RequiresPermissionMixin, ProjectNavbarMixin, MultiFormMixin):

    # override to some sensible defaults
    template_name = 'versions/manage.html'
    model = Version
    slug_url_kwarg = 'version'
    slug_field = 'name'
    context_object_name = 'version'

    permissions = ('versions.manage',)

    active_project_tab = 'versions'

    def construct_forms(self):
        return {
            'describe_form': EditVersionForm(instance=self.object),
            'new_file_form': NewFileForm(version=self.object),
        }

    def get_queryset(self):
        return Version.objects.as_user(self.request.user).filter(project__namespace__name=self.kwargs['namespace'], project__name=self.kwargs['project']).select_related('project')

    def get_namespace(self):
        if not hasattr(self, "_namespace"):
            self._namespace = get_object_or_404(Namespace.objects.as_user(
                self.request.user).select_subclasses(), name=self.kwargs['namespace'])
            return self._namespace
        else:
            return self._namespace

    def get_context_data(self, **kwargs):
        context = super(VersionsManageMixin, self).get_context_data(**kwargs)
        context['namespace'] = self.get_namespace()
        context['proj'] = context['version'].project
        return context


class VersionsManageView(VersionsManageMixin, UpdateView):

    form_name = 'describe_form'
    form_class = EditVersionForm


class VersionsDeleteView(VersionsManageView):
    permissions = ('versions.delete',)


class VersionsUploadView(VersionsManageMixin, SingleObjectMixin, FormView):

    form_name = 'new_file_form'
    form_class = NewFileForm

    permissions = ('file.create',)

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        return super(VersionsUploadView, self).get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        return super(VersionsUploadView, self).post(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super(VersionsUploadView, self).get_form_kwargs()
        kwargs['version'] = self.object
        return kwargs

    def form_valid(self, form):
        # create the new file
        file_obj = form.cleaned_data['file']

        file = File(
            project=self.object.project,
            version=self.object,
            file=form.cleaned_data['file'],
            file_name=form.cleaned_data['file_name'],
            file_extension=form.cleaned_data['file_extension'],
            file_size=file_obj.size,
            plugin_id=None,
        )
        file.save()
        return redirect(reverse('versions-manage', kwargs={'namespace': self.kwargs['namespace'], 'project': self.kwargs['project'], 'version': self.kwargs['version']}))


class FileDeleteView(DeleteView):

    http_method_names = ['post']

    def get_queryset(self):
        qs = File.objects.as_user(self.request.user).filter(version__project__namespace__name=self.kwargs['namespace'], version__project__name=self.kwargs['project'], version__name=self.kwargs['version'])
        qs = qs.filter(plugin_id=None)  # must be non-primary file!
        return qs.filter(file_name=self.kwargs['file'], file_extension=self.kwargs['file_extension'])

    def get_object(self):
        qs = self.get_queryset()

        try:
            return qs.get()
        except qs.model.DoesNotExist:
            raise Http404("No File found matching the query")

    def get_success_url(self):
        return reverse('versions-manage', kwargs={'namespace': self.kwargs['namespace'], 'project': self.kwargs['project'], 'version': self.kwargs['version']})


class ChannelsListView(RequiresPermissionMixin, DetailView):
    model = Project
    slug_field = 'name'
    slug_url_kwarg = 'project'

    template_name = 'channels/manage.html'
    context_object_name = 'proj'

    def get_permissions(self, request, *args, **kwargs):
        if request.method.lower() == 'post':
            return ('project.manage', 'channel.create')
        return ('project.manage',)

    def get_queryset(self):
        return Project.objects.as_user(self.request.user).filter(namespace__name=self.kwargs['namespace'], name=self.kwargs['project'])

    def get_context_data(self, **kwargs):
        context = super(ChannelsListView, self).get_context_data(**kwargs)
        context['form'] = NewChannelForm(
            initial={'name': 'my awesome new channel'},
            used_colours=self.object.channel_set.values_list('hex', flat=True))
        context['active_project_tab'] = 'versions'
        return context

    def post(self, request, *args, **kwargs):
        self.object = project = self.get_object()
        form = NewChannelForm(request.POST)
        if form.is_valid():
            channel = form.save(commit=False)
            channel.project = project
            channel.save()
            form = NewChannelForm()
        return self.get(request, *args, **kwargs)


class DeleteChannelView(RequiresPermissionMixin, FormView):
    template_name = "channels/confirmdelete.html"
    form_class = ChannelDeleteForm
    permissions = ('project.manage', 'channel.delete',)

    def get_context_data(self, **kwargs):
        context = super(DeleteChannelView, self).get_context_data(**kwargs)
        context['proj'] = Project.objects.as_user(self.request.user).get(
            name=self.kwargs['project'], namespace__name=self.kwargs['namespace'])
        context['channel'] = Channel.objects.get(
            pk=self.kwargs['channel'], project=context['proj'])
        context['active_project_tab'] = 'versions'
        return context

    def get_project(self):
        return get_object_or_404(
            Project.objects.as_user(self.request.user),
            name=self.kwargs['project'], namespace__name=self.kwargs['namespace'])

    def get_form(self, **kwargs):
        project = self.get_project()
        return ChannelDeleteForm(
            project,
            Channel.objects.get(pk=self.kwargs['channel'], project=project),
            **self.get_form_kwargs())

    def form_valid(self, form):
        project = self.get_project()
        channel = get_object_or_404(
            Channel, pk=self.kwargs['channel'], project=project)
        if form.cleaned_data['transfer_to'] == "DEL":
            channel.delete()
        else:
            versions_to_transfer = Version.objects.filter(channel=channel)
            new_channel = get_object_or_404(
                Channel,
                pk=form.cleaned_data['transfer_to'], project=project)
            versions_to_transfer.update(channel=new_channel)
            channel.delete()
        return redirect('project-channels', namespace=project.namespace.name, project=project.name)


class EditChannelView(RequiresPermissionMixin, FormView):
    template_name = "channels/manage.html"
    form_class = NewChannelForm
    permissions = ('project.manage', 'channel.edit',)

    def get_context_data(self, **kwargs):
        context = super(EditChannelView, self).get_context_data(**kwargs)
        context['proj'] = self.get_project()
        context['editing'] = True
        context['active_project_tab'] = 'versions'
        return context

    def get_project(self):
        return get_object_or_404(
            Project.objects.as_user(self.request.user), namespace__name=self.kwargs['namespace'], name=self.kwargs['project'])

    def get_form(self, **kwargs):
        project = self.get_project()
        channel = Channel.objects.get(
            pk=self.kwargs['channel'], project=project)
        return NewChannelForm(instance=channel,
                              used_colours=project.channel_set.values_list(
                                  'hex', flat=True),
                              **self.get_form_kwargs())

    def form_valid(self, form):
        project = self.get_project()
        channel = get_object_or_404(
            Channel, pk=self.kwargs['channel'], project=project)
        channel = form.save(commit=False)
        channel.project = project
        channel.save()
        return redirect('project-channels', namespace=project.namespace.name, project=project.name)
