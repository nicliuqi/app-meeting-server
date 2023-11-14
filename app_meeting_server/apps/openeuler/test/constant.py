# -*- coding: utf-8 -*-
# @Time    : 2023/11/15 17:09
# @Author  : Tom_zc
# @FileName: constant.py
# @Software: PyCharm


xss_script = """<div id="root"></div>

<script type="application/javascript">
  // 假设这是请求返回的数据
  const res = ['1', '2', '3', '<img src="1" onerror="console.log(windwo.localStorage)" />'];

  const root = document.querySelector('#root');

  res.forEach((item) => {
    const p = document.createElement('p');
    p.innerHTML = item;
    root.append(p);
  });
</script>"""

html_text = "https://xxx.com"

crlf_text = "/r/n"
