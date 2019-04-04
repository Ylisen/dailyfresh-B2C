#!usr/bin/env python
# -*- coding:utf-8 -*-

from django.core.files.storage import Storage
from django.conf import settings
from fdfs_client.client import Fdfs_client


class FDFSStorage(Storage):
    """fastdfs 文件存储类"""
    def __init__(self, client_conf=None, base_url=None):
        """初始化"""
        if client_conf is None:
            client_conf = settings.FDFS_CLIENT_CONF
        self.client_conf = client_conf

        if base_url is None:
            base_url = settings.FDFS_URL
        self.base_url = base_url

    def _open(self, name, mode='rb'):
        # 打开文件时使用
        pass

    def _save(self, name, content):
        # 保存文件时使用
        # name: 保存文件名字
        # content: 包含上传文件内容的File对象

        # 创建一个Fdfs_client对象
        client = Fdfs_client(self.client_conf)

        # 上传文件到fastdfs系统中
        res = client.upload_by_buffer(content.read())

        # res 返回 dict
        # {
        #     'Group name': group_name,
        #     'Remote file_id': remote_file_id,
        #     'Status': 'Upload successed.',
        #     'Local file name': local_file_name,
        #     'Uploaded size': upload_size,
        #     'Storage IP': storage_ip
        # }
        if res.get('Status') != 'Upload successed.':
            raise Exception('上传文件到FastDFS失败')

        # 获取返回的文件ID
        filename = res.get('Remote file_id')

        return filename

    def exists(self, name):
        """Django判断文件名是否可用"""
        return False

    def url(self, name):
        """返回访问文件url路径"""
        return self.base_url + name


