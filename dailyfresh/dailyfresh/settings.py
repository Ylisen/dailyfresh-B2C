# -*-coding:utf-8-*-

import os
import sys

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

sys.path.insert(0, os.path.join(BASE_DIR, 'apps'))

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/2.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = '@df*2oxkw%13&whp-3+^f)1ys8v*2hx%(albx)x(6-rhm8gj@='

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = []


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'tinymce',  # 富文本编辑器
    'haystack',  # 注册全文检索框架
    'apps.user',  # 用户模块
    'apps.cart',  # 购物车模块
    'apps.goods',  # 商品模块
    'apps.order',  # 订单模块
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'dailyfresh.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'dailyfresh.wsgi.application'


# Database
# https://docs.djangoproject.com/en/2.1/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'dailyfresh',
        'USER': 'root',
        'PASSWORD': 'Mathkk123+-',
        'HOST': '192.168.229.130',
        'PORT': '3306',
    }
}

# django认证系统使用的模型类
AUTH_USER_MODEL = 'user.User'

# Password validation
# https://docs.djangoproject.com/en/2.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/2.1/topics/i18n/

LANGUAGE_CODE = 'zh-hans'

TIME_ZONE = 'Asia/Shanghai'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/2.1/howto/static-files/

STATIC_URL = '/static/'
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]
# 指定收集静态文件的路径
# STATIC_ROOT = 'var/www/dailyfresh/static'

# 富文本编辑器配置
TINYMCE_DEFAULT_CONFIG = {
    'theme': 'advanced',
    'width': 600,
    'height':  400,
}

# 发送邮件配置
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
# EMAIL_USE_TLS = False   # 是否使用TLS安全传输协议(用于在两个通信应用程序之间提供保密性和数据完整性。)
# EMAIL_USE_SSL = True    # 是否使用SSL加密，qq企业邮箱要求使用
EMAIL_HOST = 'smtp.163.com'   # 发送邮件的邮箱的SMTP服务器，这里用了163邮箱
EMAIL_PORT = 25     # 发件箱的SMTP服务器端口
EMAIL_HOST_USER = 'Ylisen10@163.com'    # 发送邮件的邮箱地址
EMAIL_HOST_PASSWORD = 'dailyfresh123'   # 发送邮件的邮箱密码(这里使用的是授权码)
EMAIL_PROM = '天天生鲜<Ylisen10@163.com>'  # 收件人看到的发件人

# django的缓存配置, 使用redis
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://192.168.229.130:6379/1",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        }
    }
}

# 配置session存储
SESSION_ENGINE = "django.contrib.sessions.backends.cache"
SESSION_CACHE_ALIAS = "default"

# 配置登录url地址
LOGIN_URL = '/user/login'

# 设置Django的文件存储类
DEFAULT_FILE_STORAGE = 'utils.fdfs.storage.FDFSStorage'

# 设置fdfs使用的client.conf文件路径
FDFS_CLIENT_CONF = './utils/fdfs/client.conf'

# 设置fdfs存储服务器上nginx的IP和端口号
FDFS_URL = 'http://192.168.229.130:80/'


# 全文检索框架配置
HAYSTACK_CONNECTIONS = {
    'default': {
        # 使用whoosh引擎
        # 'ENGINE': 'haystack.backends.whoosh_backend.WhooshEngine',
        'ENGINE': 'haystack.backends.whoosh_cn_backend.WhooshEngine',
        # 索引文件路径
        'PATH': os.path.join(os.path.dirname(__file__), 'whoosh_index'),
    },
}

# 当添加、修改、删除数据时，自动生成索引
HAYSTACK_SIGNAL_PROCESSOR = 'haystack.signals.RealtimeSignalProcessor'

HAYSTACK_SEARCH_RESULTS_PER_PAGE = 6  # 指定搜索结果每页显示多少条信息
