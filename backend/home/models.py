from django.db import models
import markdown

class App(models.Model):
    """A model for an app."""
    author = models.CharField(max_length=255, help_text='The author of the app.')
    branch = models.CharField(max_length=255, default='main', help_text='The git branch of the app.')
    category = models.ForeignKey('Category', on_delete=models.CASCADE, related_name='apps', help_text='The category of the app.')
    changelog = models.TextField(help_text='A changelog for the app.')
    description = models.TextField(help_text='A full description of the app.')
    fap_id = models.CharField(max_length=255, unique=True, help_text='The unique ID of the app.')
    icon = models.CharField(max_length=255, help_text='The icon URL of the app.')
    location_origin = models.CharField(max_length=255, help_text='The Github URL of the repo')
    location_subdir = models.CharField(max_length=255, null=True, blank=True, help_text='The subdirectory within the repo where the app is located, ex: "apps/myapp"')
    my_order = models.BigIntegerField(default=0, null=False, blank=False)
    name = models.CharField(max_length=255, help_text='The name of the app.')
    screenshots = models.JSONField(help_text='A list of screenshot URLs for the app.')
    short_description = models.CharField(max_length=255, help_text='A short description of the app.')
    version = models.CharField(max_length=255, help_text='The version of the app.')

    def __str__(self) -> str:
        return self.name
    
    @property
    def changelog_html(self) -> str:
        """Returns the changelog rendered as HTML."""
        return markdown.markdown(self.changelog)
    
    @property
    def description_html(self) -> str:
        """Returns the description rendered as HTML."""
        return markdown.markdown(self.description)
    
    @property
    def json(self) -> dict:
        """Returns a JSON representation of the app."""
        return {
            'author': self.author,
            'branch': self.branch,
            'category': self.category.name,
            'changelog': self.changelog_html,
            'description': self.description_html,
            'fap_id': self.fap_id,
            'icon': self.icon,
            'name': self.name,
            'screenshots': self.screenshots,
            'short_description': self.short_description,
            'version': self.version,
        }
    
    class Meta:
        ordering = ['my_order']
        verbose_name = 'App'
        verbose_name_plural = 'Apps'

class Category(models.Model):
    """A model for an app category."""
    my_order = models.BigIntegerField(default=0, null=False, blank=False)
    name = models.CharField(max_length=255, help_text='The name of the category.')

    def __str__(self) -> str:
        return self.name
    
    class Meta:
        ordering = ['my_order']
        verbose_name = 'Category'
        verbose_name_plural = 'Categories'

class Firmware(models.Model):
    """A model for a firmware."""
    description = models.TextField(help_text='A description of the firmware.')
    firmware_id = models.CharField(max_length=255, unique=True, help_text='The unique ID of the firmware.')
    my_order = models.BigIntegerField(default=0, null=False, blank=False)
    name = models.CharField(max_length=255, help_text='The name of the firmware.')
    version = models.CharField(max_length=255, help_text='The version of the firmware.')

    def __str__(self) -> str:
        return self.name
    
    class Meta:
        ordering = ['my_order']
        verbose_name = 'Firmware'
        verbose_name_plural = 'Firmwares'
    

class SyncRun(models.Model):
    """Tracks a sync operation from the Flipper application catalog."""

    class Status(models.TextChoices):
        CANCELLED = 'cancelled', 'Cancelled'
        COMPLETED = 'completed', 'Completed'
        FAILED = 'failed', 'Failed'
        RUNNING = 'running', 'Running'

    error_message = models.TextField(blank=True, default='')
    finished_at = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.RUNNING,
    )
    total_processed = models.IntegerField(default=0,
        help_text='Total number of apps processed during this sync.')

    def __str__(self) -> str:
        return f"SyncRun #{self.id} — {self.status} ({self.started_at:%Y-%m-%d %H:%M})"

    class Meta:
        ordering = ['-started_at']
        verbose_name = 'Sync Run'
        verbose_name_plural = 'Sync Runs'

class Build(models.Model):
    app = models.ForeignKey(App, on_delete=models.CASCADE, related_name="builds")
    firmware = models.ForeignKey(Firmware, on_delete=models.CASCADE)
    file = models.FileField(upload_to="faps/")
    size = models.PositiveIntegerField()
    md5 = models.CharField(max_length=32, blank=True)
    built_at = models.DateTimeField(auto_now_add=True)
    commit = models.CharField(max_length=40, blank=True) # source commit the .fap was built from

    class Meta:
        unique_together = ("app", "firmware")   # one cached build per (app, firmware)

    def __str__(self):
        return f"{self.app.name} / {self.firmware} build"

class BuildJob(models.Model):
    app = models.ForeignKey(App, on_delete=models.CASCADE)
    firmware = models.ForeignKey(Firmware, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, default="pending")  # pending|running|done|failed
    percent = models.PositiveIntegerField(default=0)
    message = models.CharField(max_length=255, blank=True)
    error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

# Parameters for external apps: https://developer.flipper.net/flipperzero/doxygen/app_manifests.html
# sources: list of strings, file name masks used for gathering sources within the app folder. The default value of ["*.c*"] includes C and C++ source files. Apps cannot use the "lib" folder for their own source code, as it is reserved for fap_private_libs. Paths starting with "!" are excluded from the list of sources. They can also include wildcard characters and directory names. For example, a value of ["*.c*", "!plugins"] will include all C and C++ source files in the app folder except those in the plugins (and lib) folders. Paths with no wildcards (*, ?) are treated as full literal paths for both inclusion and exclusion.
# fap_version: string, app version. The default value is "0.1". You can also use a tuple of 2 numbers in the form of (x,y) to specify the version. It is also possible to add more dot-separated parts to the version, like patch number, but only major and minor version numbers are stored in the built .fap.
# fap_icon: name of a .png file, 1-bit color depth, 10x10px, to be embedded within .fap file.
# fap_libs: list of extra libraries to link the app against. Provides access to extra functions that are not exported as a part of main firmware at the expense of increased .fap file size and RAM consumption.
# fap_category: string, may be empty. App subcategory, also determines the path of the FAP within the apps folder in the file system.
# fap_description: string, may be empty. Short app description.
# fap_author: string, may be empty. App's author.
# fap_weburl: string, may be empty. App's homepage.
# fap_icon_assets: string. If present, it defines a folder name to be used for gathering image assets for this app. These images will be preprocessed and built alongside the app. See FAP assets for details.
# fap_extbuild: provides support for parts of app sources to be built by external tools. Contains a list of ExtFile(path="file name", command="shell command") definitions. fbt will run the specified command for each file in the list.
# fal_embedded: boolean, default False. Applies only to PLUGIN type. If True, the plugin will be embedded into host app's .fap file as a resource and extracted to apps_assets/APPID folder on its start. This allows plugins to be distributed as a part of the host app.
