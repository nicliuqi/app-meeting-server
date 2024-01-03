"""
bilibili_api.dynamic

动态相关
"""

from .utils import utils
from .utils.picture import Picture
from .utils.credential import Credential
from .utils.network import Api

API = utils.get_api("dynamic")


async def upload_image(
        image: Picture, credential: Credential, data: dict = None
) -> dict:
    """
    上传动态图片

    Args:
        image (Picture)   : 图片流. 有格式要求.

        credential (Credential): 凭据

        data (dict): 自定义请求体
    Returns:
        dict: 调用 API 返回的结果
    """
    credential.raise_for_no_sessdata()
    credential.raise_for_no_bili_jct()

    api = API["send"]["upload_img"]
    raw = image.content

    if data is None:
        data = {"biz": "new_dyn", "category": "daily"}

    files = {"file_up": raw}
    return_info = (
        await Api(**api, credential=credential).update_data(**data).request(files=files)
    )
    return return_info
