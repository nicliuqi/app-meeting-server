"""
bilibili_api.video_uploader

视频上传
"""
import os
import json
import time
import base64
import random
import asyncio
from enum import Enum
from typing import List, Union
from copy import copy, deepcopy
from asyncio.tasks import Task, create_task
from asyncio.exceptions import CancelledError

from .utils.utils import get_api
from .utils.picture import Picture
from .utils.AsyncEvent import AsyncEvent
from .utils.credential import Credential
from .exceptions.ApiException import ApiException
from .utils.network import Api, get_session
from .exceptions.NetworkException import NetworkException
from .exceptions.ResponseCodeException import ResponseCodeException

# import ffmpeg

_API = get_api("video_uploader")


async def _upload_cover(cover: Picture, credential: Credential):
    api = _API["cover_up"]
    cover = cover.convert_format("png")
    data = {
        "cover": f'data:image/png;base64,{base64.b64encode(cover.content).decode("utf-8")}'
    }
    return await Api(**api, credential=credential).update_data(**data).result


class VideoUploaderPage:
    """
    分 P 对象
    """

    def __init__(self, path: str, title: str, description: str = ""):
        """
        Args:
            path (str): 视频文件路径
            title        (str)           : 视频标题
            description  (str, optional) : 视频简介. Defaults to "".
        """
        self.path = path
        self.title: str = title
        self.description: str = description

        self.cached_size: Union[int, None] = None

    def get_size(self) -> int:
        """
        获取文件大小

        Returns:
            int: 文件大小
        """
        if self.cached_size is not None:
            return self.cached_size

        size: int = 0
        stream = open(self.path, "rb")
        while True:
            s: bytes = stream.read(1024)

            if not s:
                break

            size += len(s)

        stream.close()

        self.cached_size = size
        return size


class VideoUploaderEvents(Enum):
    """
    上传事件枚举

    Events:
    + PRE_PAGE 上传分 P 前
    + PREUPLOAD  获取上传信息
    + PREUPLOAD_FAILED  获取上传信息失败
    + PRE_CHUNK  上传分块前
    + AFTER_CHUNK  上传分块后
    + CHUNK_FAILED  区块上传失败
    + PRE_PAGE_SUBMIT  提交分 P 前
    + PAGE_SUBMIT_FAILED  提交分 P 失败
    + AFTER_PAGE_SUBMIT  提交分 P 后
    + AFTER_PAGE  上传分 P 后
    + PRE_COVER  上传封面前
    + AFTER_COVER  上传封面后
    + COVER_FAILED  上传封面失败
    + PRE_SUBMIT  提交视频前
    + SUBMIT_FAILED  提交视频失败
    + AFTER_SUBMIT  提交视频后
    + COMPLETED  完成上传
    + ABORTED  用户中止
    + FAILED  上传失败
    """

    PREUPLOAD = "PREUPLOAD"
    PREUPLOAD_FAILED = "PREUPLOAD_FAILED"
    PRE_PAGE = "PRE_PAGE"

    PRE_CHUNK = "PRE_CHUNK"
    AFTER_CHUNK = "AFTER_CHUNK"
    CHUNK_FAILED = "CHUNK_FAILED"

    PRE_PAGE_SUBMIT = "PRE_PAGE_SUBMIT"
    PAGE_SUBMIT_FAILED = "PAGE_SUBMIT_FAILED"
    AFTER_PAGE_SUBMIT = "AFTER_PAGE_SUBMIT"

    AFTER_PAGE = "AFTER_PAGE"

    PRE_COVER = "PRE_COVER"
    AFTER_COVER = "AFTER_COVER"
    COVER_FAILED = "COVER_FAILED"

    PRE_SUBMIT = "PRE_SUBMIT"
    SUBMIT_FAILED = "SUBMIT_FAILED"
    AFTER_SUBMIT = "AFTER_SUBMIT"

    COMPLETED = "COMPLETE"
    ABORTED = "ABORTED"
    FAILED = "FAILED"


class VideoUploader(AsyncEvent):
    """
    视频上传

    Attributes:
        pages        (List[VideoUploaderPage]): 分 P 列表

        meta         (dict)                   : 视频信息

        credential   (Credential)             : 凭据

        cover_path   (str)                    : 封面路径
    """

    def __init__(
            self,
            pages: List[VideoUploaderPage],
            meta: dict,
            credential: Credential,
            cover: Union[str, Picture] = "",
            #  ffprobe_path: str = 'ffprobe'
    ):
        """
        Args:
            pages        (List[VideoUploaderPage]): 分 P 列表

            meta         (dict)                   : 视频信息

            credential   (Credential)             : 凭据

            cover        (str | Picture)          : 封面路径 / Picture 对象

        meta 参数示例：

        ```json
        {
            "title": "",
            "copyright": 1,
            "tid": 130,
            "tag": "",
            "desc_format_id": 9999,
            "desc": "",
            "recreate": -1,
            "dynamic": "",
            "interactive": 0,
            "act_reserve_create": 0,
            "no_disturbance": 0,
            "no_reprint": 1,
            "subtitle": {
                "open": 0,
                "lan": "",
            },
            "dolby": 0,
            "lossless_music": 0,
            "web_os": 1,
        }
        ```

        meta 保留字段：videos, cover
        """
        super().__init__()
        self.meta = meta
        self.pages = pages
        self.credential = credential
        self.cover_path = cover
        # self.ffprobe_path = ffprobe_path
        self.__task: Union[Task, None] = None

    async def _preupload(self, page: VideoUploaderPage) -> dict:
        """
        分 P 上传初始化

        Returns:
            dict: 初始化信息
        """
        self.dispatch(VideoUploaderEvents.PREUPLOAD.value, {page: page})
        api = _API["preupload"]

        # 首先获取视频文件预检信息
        session = get_session()

        resp = await session.get(
            api["url"],
            params={
                "profile": "ugcfx/bup",
                "name": os.path.basename(page.path),
                "size": page.get_size(),
                "r": "upos",
                "ssl": "0",
                "version": "2.10.4",
                "build": "2100400",
                "upcdn": "bda2",
                "probe_version": "20211012",
            },
            cookies=self.credential.get_cookies(),
            headers={
                "User-Agent": "Mozilla/5.0",
                "Referer": "https://www.bilibili.com",
            },
        )
        if resp.status_code >= 400:
            self.dispatch(VideoUploaderEvents.PREUPLOAD_FAILED.value, {page: page})
            raise NetworkException(resp.status_code, resp.reason_phrase)

        preupload = resp.json()

        if preupload["OK"] != 1:
            self.dispatch(VideoUploaderEvents.PREUPLOAD_FAILED.value, {page: page})
            raise ApiException(json.dumps(preupload))

        url = self._get_upload_url(preupload)

        # 获取 upload_id
        resp = await session.post(
            url,
            headers={
                "x-upos-auth": preupload["auth"],
                "user-agent": "Mozilla/5.0",
                "referer": "https://www.bilibili.com",
            },
            params={
                "uploads": "",
                "output": "json",
                "profile": "ugcfx/bup",
                "filesize": page.get_size(),
                "partsize": preupload["chunk_size"],
                "biz_id": preupload["biz_id"],
            },
        )
        if resp.status_code >= 400:
            self.dispatch(VideoUploaderEvents.PREUPLOAD_FAILED.value, {page: page})
            raise ApiException("获取 upload_id 错误")

        data = json.loads(resp.text)

        if data["OK"] != 1:
            self.dispatch(VideoUploaderEvents.PREUPLOAD_FAILED.value, {page: page})
            raise ApiException("获取 upload_id 错误：" + json.dumps(data))

        preupload["upload_id"] = data["upload_id"]

        return preupload

    async def _main(self) -> dict:
        videos = []
        for page in self.pages:
            data = await self._upload_page(page)
            videos.append(
                {
                    "title": page.title,
                    "desc": page.description,
                    "filename": data["filename"],  # type: ignore
                    "cid": data["cid"],  # type: ignore
                }
            )

        cover_url = ""

        if self.cover_path:
            cover_url = await self._upload_cover()

        result = await self._submit(videos, cover_url)

        self.dispatch(VideoUploaderEvents.COMPLETED.value, result)
        return result

    async def start(self) -> dict:  # type: ignore
        """
        开始上传

        Returns:
            dict: 返回带有 bvid 和 aid 的字典。
        """

        task = create_task(self._main())
        self.__task = task

        try:
            result = await task
            self.__task = None
            return result
        except CancelledError:
            # 忽略 task 取消异常
            pass
        except Exception as e:
            self.dispatch(VideoUploaderEvents.FAILED.value, {"err": e})
            raise e

    async def _upload_cover(self) -> str:
        """
        上传封面

        Returns:
            str: 封面 URL
        """
        self.dispatch(VideoUploaderEvents.PRE_COVER.value, None)
        try:
            pic = (
                self.cover_path
                if isinstance(self.cover_path, Picture)
                else Picture().from_file(self.cover_path)
            )
            resp = await _upload_cover(pic, self.credential)
            self.dispatch(VideoUploaderEvents.AFTER_COVER.value, {"url": resp["url"]})
            return resp["url"]
        except Exception as e:
            self.dispatch(VideoUploaderEvents.COVER_FAILED.value, {"err": e})
            raise e

    async def _upload_page(self, page: VideoUploaderPage) -> dict:
        """
        上传分 P

        Args:
            page (VideoUploaderPage): 分 P 对象

        Returns:
            str: 分 P 文件 ID，用于 submit 时的 $.videos[n].filename 字段使用。
        """
        preupload = await self._preupload(page)
        self.dispatch(VideoUploaderEvents.PRE_PAGE.value, {"page": page})

        page_size = page.get_size()
        # 所有分块起始位置
        chunk_offset_list = list(range(0, page_size, preupload["chunk_size"]))
        # 分块总数
        total_chunk_count = len(chunk_offset_list)
        # 并发上传分块
        chunk_number = 0
        # 上传队列
        chunks_pending = []
        # 缓存 upload_id，这玩意只能从上传的分块预检结果获得
        upload_id = preupload["upload_id"]
        for offset in chunk_offset_list:
            chunks_pending.insert(
                0,
                self._upload_chunk(
                    page, offset, chunk_number, total_chunk_count, preupload
                ),
            )
            chunk_number += 1

        while chunks_pending:
            tasks = []

            while len(tasks) < preupload["threads"] and len(chunks_pending) > 0:
                tasks.append(create_task(chunks_pending.pop()))

            result = await asyncio.gather(*tasks)

            for r in result:
                if not r["ok"]:
                    chunks_pending.insert(
                        0,
                        self._upload_chunk(
                            page,
                            r["offset"],
                            r["chunk_number"],
                            total_chunk_count,
                            preupload,
                        ),
                    )

        data = await self._complete_page(page, total_chunk_count, preupload, upload_id)

        self.dispatch(VideoUploaderEvents.AFTER_PAGE.value, {"page": page})

        return data

    @staticmethod
    def _get_upload_url(preupload: dict) -> str:
        # 上传目标 URL
        return (
                "https:"
                + random.choice(preupload["endpoints"])
                + "/"
                + preupload["upos_uri"].removeprefix("upos://")
        )

    async def _upload_chunk(
            self,
            page: VideoUploaderPage,
            offset: int,
            chunk_number: int,
            total_chunk_count: int,
            preupload: dict,
    ) -> dict:
        """
        上传视频分块

        Args:
            page (VideoUploaderPage): 分 P 对象
            offset (int): 分块起始位置
            chunk_number (int): 分块编号
            total_chunk_count (int): 总分块数
            preupload (dict): preupload 数据

        Returns:
            dict: 上传结果和分块信息。
        """
        chunk_event_callback_data = {
            "page": page,
            "offset": offset,
            "chunk_number": chunk_number,
            "total_chunk_count": total_chunk_count,
        }
        self.dispatch(VideoUploaderEvents.PRE_CHUNK.value, chunk_event_callback_data)
        session = get_session()

        stream = open(page.path, "rb")
        stream.seek(offset)
        chunk = stream.read(preupload["chunk_size"])
        stream.close()

        # 上传目标 URL
        url = self._get_upload_url(preupload)

        err_return = {
            "ok": False,
            "chunk_number": chunk_number,
            "offset": offset,
            "page": page,
        }

        real_chunk_size = len(chunk)

        params = {
            "partNumber": str(chunk_number + 1),
            "uploadId": str(preupload["upload_id"]),
            "chunk": str(chunk_number),
            "chunks": str(total_chunk_count),
            "size": str(real_chunk_size),
            "start": str(offset),
            "end": str(offset + real_chunk_size),
            "total": page.get_size(),
        }

        ok_return = {
            "ok": True,
            "chunk_number": chunk_number,
            "offset": offset,
            "page": page,
        }

        try:
            resp = await session.put(
                url,
                data=chunk,  # type: ignore
                params=params,
                headers={"x-upos-auth": preupload["auth"]},
            )
            if resp.status_code >= 400:
                chunk_event_callback_data["info"] = f"Status {resp.status_code}"
                self.dispatch(
                    VideoUploaderEvents.CHUNK_FAILED.value,
                    chunk_event_callback_data,
                )
                return err_return

            data = resp.text

            if data != "MULTIPART_PUT_SUCCESS" and data != "":
                chunk_event_callback_data["info"] = "分块上传失败"
                self.dispatch(
                    VideoUploaderEvents.CHUNK_FAILED.value,
                    chunk_event_callback_data,
                )
                return err_return

        except Exception as e:
            chunk_event_callback_data["info"] = str(e)
            self.dispatch(
                VideoUploaderEvents.CHUNK_FAILED.value, chunk_event_callback_data
            )
            return err_return

        self.dispatch(VideoUploaderEvents.AFTER_CHUNK.value, chunk_event_callback_data)
        return ok_return

    async def _complete_page(
            self, page: VideoUploaderPage, chunks: int, preupload: dict, upload_id: str
    ) -> dict:
        """
        提交分 P 上传

        Args:
            page (VideoUploaderPage): 分 P 对象

            chunks (int): 分块数量

            preupload (dict): preupload 数据

            upload_id (str): upload_id

        Returns:
            dict: filename: 该分 P 的标识符，用于最后提交视频。cid: 分 P 的 cid
        """
        self.dispatch(VideoUploaderEvents.PRE_PAGE_SUBMIT.value, {"page": page})

        data = {
            "parts": list(
                map(lambda x: {"partNumber": x, "eTag": "etag"}, range(1, chunks + 1))
            )
        }

        params = {
            "output": "json",
            "name": os.path.basename(page.path),
            "profile": "ugcfx/bup",
            "uploadId": upload_id,
            "biz_id": preupload["biz_id"],
        }

        url = self._get_upload_url(preupload)

        session = get_session()

        resp = await session.post(
            url=url,
            data=json.dumps(data),  # type: ignore
            headers={
                "x-upos-auth": preupload["auth"],
                "content-type": "application/json; charset=UTF-8",
            },
            params=params,
        )
        if resp.status_code >= 400:
            err = NetworkException(resp.status_code, "状态码错误，提交分 P 失败")
            self.dispatch(
                VideoUploaderEvents.PAGE_SUBMIT_FAILED.value,
                {"page": page, "err": err},
            )
            raise err

        data = json.loads(resp.read())

        if data["OK"] != 1:
            err = ResponseCodeException(-1, f'提交分 P 失败，原因: {data["message"]}')
            self.dispatch(
                VideoUploaderEvents.PAGE_SUBMIT_FAILED.value,
                {"page": page, "err": err},
            )
            raise err

        self.dispatch(VideoUploaderEvents.AFTER_PAGE_SUBMIT.value, {"page": page})

        return {
            "filename": os.path.splitext(data["key"].removeprefix("/"))[0],
            "cid": preupload["biz_id"],
        }

    async def _submit(self, videos: list, cover_url: str = "") -> dict:
        """
        提交视频

        Args:
            videos (list): 视频列表

            cover_url (str, optional): 封面 URL.

        Returns:
            dict: 含 bvid 和 aid 的字典
        """
        meta = copy(self.meta)
        meta["cover"] = cover_url
        meta["videos"] = videos

        self.dispatch(VideoUploaderEvents.PRE_SUBMIT.value, deepcopy(meta))

        meta["csrf"] = self.credential.bili_jct  # csrf 不需要 print
        api = _API["submit"]

        try:
            params = {"csrf": self.credential.bili_jct, "t": time.time() * 1000}
            headers = {"content-type": "application/json"}
            resp = (
                await Api(
                    **api, credential=self.credential, no_csrf=True, json_body=True
                )
                    .update_params(**params)
                    .update_data(**meta)
                    .update_headers(**headers)
                    .result
            )
            self.dispatch(VideoUploaderEvents.AFTER_SUBMIT.value, resp)
            return resp

        except Exception as err:
            self.dispatch(VideoUploaderEvents.SUBMIT_FAILED.value, {"err": err})
            raise err

    async def abort(self):
        """
        中断上传
        """
        if self.__task:
            self.__task.cancel("用户手动取消")

        self.dispatch(VideoUploaderEvents.ABORTED.value, None)
