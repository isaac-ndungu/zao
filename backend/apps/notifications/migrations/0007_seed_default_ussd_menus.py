from django.db import migrations


DEFAULT_MENUS = [
    {
        'menu_key': 'home',
        'language': 'en',
        'title': 'Welcome to Zao Cooperative.\nEnter your member number:',
        'options': [],
        'order': 0,
    },
    {
        'menu_key': 'menu',
        'language': 'en',
        'title': 'Main Menu',
        'options': [
            {'key': '1', 'label': 'My Deliveries', 'action': 'deliveries'},
            {'key': '2', 'label': 'My Payments', 'action': 'payments'},
            {'key': '3', 'label': 'My Profile', 'action': 'profile'},
        ],
        'order': 1,
    },
    {
        'menu_key': 'deliveries',
        'language': 'en',
        'title': 'Recent deliveries:',
        'options': [{'key': '0', 'label': 'Back', 'action': 'menu'}],
        'order': 2,
    },
    {
        'menu_key': 'home',
        'language': 'sw',
        'title': 'Karibu Zao Cooperative.\nWeka nambari yako ya mwanachama:',
        'options': [],
        'order': 0,
    },
    {
        'menu_key': 'menu',
        'language': 'sw',
        'title': 'Menyu Kuu',
        'options': [
            {'key': '1', 'label': 'Uwasilishaji Wangu', 'action': 'deliveries'},
            {'key': '2', 'label': 'Malipo Yangu', 'action': 'payments'},
            {'key': '3', 'label': 'Wasifu Wangu', 'action': 'profile'},
        ],
        'order': 1,
    },
    {
        'menu_key': 'deliveries',
        'language': 'sw',
        'title': 'Uwasilishaji wa hivi karibuni:',
        'options': [{'key': '0', 'label': 'Rudi', 'action': 'menu'}],
        'order': 2,
    },
]


def seed_default_menus(apps, schema_editor):
    Cooperative = apps.get_model('cooperatives', 'Cooperative')
    USSDMenuConfig = apps.get_model('notifications', 'USSDMenuConfig')

    for coop in Cooperative.objects.all():
        for menu in DEFAULT_MENUS:
            USSDMenuConfig.objects.get_or_create(
                cooperative=coop,
                menu_key=menu['menu_key'],
                language=menu['language'],
                defaults={
                    'title': menu['title'],
                    'options': menu['options'],
                    'order': menu['order'],
                },
            )


def reverse_seed(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('cooperatives', '0015_add_ussd_menu_config'),
        ('notifications', '0006_add_ussd_menu_config'),
    ]

    operations = [
        migrations.RunPython(seed_default_menus, reverse_seed),
    ]
