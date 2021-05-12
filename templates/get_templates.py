def get_html_with_summary_with_recordings():
    html = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta http-equiv="X-UA-Compatible" content="IE=edge">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Document</title>
    </head>
    <body>
        <table style="background-color: rgb(212, 207, 207); border: 0;">
            <tr>
                <td colspan="3" height="50" style="background-color: #003CBA; text-align: center; color: white; font-size: 24px;">openEuler conference</td>
            </tr>
            <tr>
                <td colspan="3" height="20" style="background-color: rgb(212, 207, 207)"></td>
            </tr>
            <tr>
                <td colspan="3" style="background-color: rgb(212, 207, 207); padding-left: 30px;">您好！</td>
            </tr>
            <tr>
                <td colspan="3" style="background-color: rgb(212, 207, 207); padding-left: 30px;">openEuler {{sig_name}} SIG 邀请您参加 {{start_time}} 召开的ZOOM会议(自动录制)</td>
            </tr>
            <tr>
                <td colspan="3" style="background-color: rgb(212, 207, 207); padding-left: 30px;">会议主题：{{topic}}</td>
            </tr>
            <tr>
                <td colspan="3" style="background-color: rgb(212, 207, 207); padding-left: 30px;">会议内容：{{summary}}</td>
            </tr>
            <tr>
                <td colspan="3" style="background-color: rgb(212, 207, 207); padding-left: 30px;">会议链接：{{join_url}}</td>
            </tr>
            <tr>
                <td colspan="3" style="background-color: rgb(212, 207, 207); padding-left: 30px;">温馨提醒：建议接入会议后修改参会人的姓名，也可以使用您在gitee.com的ID</td>
            </tr>
            <tr>
                <td colspan="3" style="background-color: rgb(212, 207, 207); padding-left: 30px;">更多资讯尽在：https://openeuler.org/zh/</td>
            </tr>
            <tr>
                <td colspan="3" height="30" style="background-color: rgb(212, 207, 207);"></td>
            </tr>
            <tr>
                <td colspan="3" style="background-color: rgb(212, 207, 207); padding-left: 30px;">Hello!</td>
            </tr>
            <tr>
                <td colspan="3"style="background-color: rgb(212, 207, 207); padding-left: 30px;">openEuler {{sig_name}} SIG invites you to attend the ZOOM conference(auto recording) will be held at {{start_time}},</td>
            </tr>
            <tr>
                <td colspan="3" style="background-color: rgb(212, 207, 207); padding-left: 30px;">Subject: {{topic}},</td>
            </tr>
            <tr>
                <td colspan="3" style="background-color: rgb(212, 207, 207); padding-left: 30px;">Summary: {{summary}}</td>
            </tr>
            <tr>
                <td colspan="3" style="background-color: rgb(212, 207, 207); padding-left: 30px;">You can join the meeting at {{join_url}}</td>
            </tr>
            <tr>
                <td colspan="3" style="background-color: rgb(212, 207, 207); padding-left: 30px;">Note: You are advised to change the participant name after joining the conference or use your ID at gitee.com.</td>
            </tr>
            <tr>
                <td colspan="3" style="background-color: rgb(212, 207, 207); padding-left: 30px;">More information: https://openeuler.org/zh/</td>
            </tr>
            <tr>
                <td colspan="3" height="30" style="background-color: rgb(212, 207, 207)"></td>
            </tr>
            <tr>
                <td width="400" height="250"><a href="{{h1}}"><img src="cid:templates/images/activities/{{s1}}" height="250" width="400" alt="openEuler meetup" /></a></td>
                <td width="400" height="250"><a href="{{h2}}"><img src="cid:templates/images/activities/{{s2}}" height="250" width="400" alt="openEuler meetup" /></a></td>
                <td width="400" height="250"><a href="{{h3}}"><img src="cid:templates/images/activities/{{s3}}" height="250" width="400" alt="openEuler meetup" /></a></td>
            </tr>
            <tr>
                <td  colspan="3" width="1200"  height="150"><a href="https://openeuler.org/zh/"><img src="cid:templates/images/foot.png" height="150" width="1210" alt="https://openeuler.org/zh/"/></a></td>
            </tr>
        </table>
    </body>
    </html>
    """
    return html


def get_html_with_summary_without_recordings():
    html = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta http-equiv="X-UA-Compatible" content="IE=edge">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Document</title>
    </head>
    <body>
        <table style="background-color: rgb(212, 207, 207); border: 0;">
            <tr>
                <td colspan="3" height="50" style="background-color: #003CBA; text-align: center; color: white; font-size: 24px;">openEuler conference</td>
            </tr>
            <tr>
                <td colspan="3" height="20" style="background-color: rgb(212, 207, 207)"></td>
            </tr>
            <tr>
                <td colspan="3" style="background-color: rgb(212, 207, 207); padding-left: 30px;">您好！</td>
            </tr>
            <tr>
                <td colspan="3" style="background-color: rgb(212, 207, 207); padding-left: 30px;">openEuler {{sig_name}} SIG 邀请您参加 {{start_time}} 召开的ZOOM会议</td>
            </tr>
            <tr>
                <td colspan="3" style="background-color: rgb(212, 207, 207); padding-left: 30px;">会议主题：{{topic}}</td>
            </tr>
            <tr>
                <td colspan="3" style="background-color: rgb(212, 207, 207); padding-left: 30px;">会议内容：{{summary}}</td>
            </tr>
            <tr>
                <td colspan="3" style="background-color: rgb(212, 207, 207); padding-left: 30px;">会议链接：{{join_url}}</td>
            </tr>
            <tr>
                <td colspan="3" style="background-color: rgb(212, 207, 207); padding-left: 30px;">温馨提醒：建议接入会议后修改参会人的姓名，也可以使用您在gitee.com的ID</td>
            </tr>
            <tr>
                <td colspan="3" style="background-color: rgb(212, 207, 207); padding-left: 30px;">更多资讯尽在：https://openeuler.org/zh/</td>
            </tr>
            <tr>
                <td colspan="3" height="30" style="background-color: rgb(212, 207, 207);"></td>
            </tr>
            <tr>
                <td colspan="3" style="background-color: rgb(212, 207, 207); padding-left: 30px;">Hello!</td>
            </tr>
            <tr>
                <td colspan="3"style="background-color: rgb(212, 207, 207); padding-left: 30px;">openEuler {{sig_name}} SIG invites you to attend the ZOOM conference will be held at {{start_time}},</td>
            </tr>
            <tr>
                <td colspan="3" style="background-color: rgb(212, 207, 207); padding-left: 30px;">Subject: {{topic}},</td>
            </tr>
            <tr>
                <td colspan="3" style="background-color: rgb(212, 207, 207); padding-left: 30px;">Summary: {{summary}}</td>
            </tr>
            <tr>
                <td colspan="3" style="background-color: rgb(212, 207, 207); padding-left: 30px;">You can join the meeting at {{join_url}}</td>
            </tr>
            <tr>
                <td colspan="3" style="background-color: rgb(212, 207, 207); padding-left: 30px;">Note: You are advised to change the participant name after joining the conference or use your ID at gitee.com.</td>
            </tr>
            <tr>
                <td colspan="3" style="background-color: rgb(212, 207, 207); padding-left: 30px;">More information: https://openeuler.org/zh/</td>
            </tr>
            <tr>
                <td colspan="3" height="30" style="background-color: rgb(212, 207, 207)"></td>
            </tr>
            <tr>
                <td width="400" height="250"><a href="{{h1}}"><img src="cid:templates/images/activities/{{s1}}" height="250" width="400" alt="openEuler meetup" /></a></td>
                <td width="400" height="250"><a href="{{h2}}"><img src="cid:templates/images/activities/{{s2}}" height="250" width="400" alt="openEuler meetup" /></a></td>
                <td width="400" height="250"><a href="{{h3}}"><img src="cid:templates/images/activities/{{s3}}" height="250" width="400" alt="openEuler meetup" /></a></td>
            </tr>
            <tr>
                <td  colspan="3" width="1200"  height="150"><a href="https://openeuler.org/zh/"><img src="cid:templates/images/foot.png" height="150" width="1210" alt="https://openeuler.org/zh/"/></a></td>
            </tr>
        </table>
    </body>
    </html>
    """
    return html


def get_html_without_summary_with_recordings():
    html = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta http-equiv="X-UA-Compatible" content="IE=edge">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Document</title>
    </head>
    <body>
        <table style="background-color: rgb(212, 207, 207); border: 0;">
            <tr>
                <td colspan="3" height="50" style="background-color: #003CBA; text-align: center; color: white; font-size: 24px;">openEuler conference</td>
            </tr>
            <tr>
                <td colspan="3" height="20" style="background-color: rgb(212, 207, 207)"></td>
            </tr>
            <tr>
                <td colspan="3" style="background-color: rgb(212, 207, 207); padding-left: 30px;">您好！</td>
            </tr>
            <tr>
                <td colspan="3" style="background-color: rgb(212, 207, 207); padding-left: 30px;">openEuler {{sig_name}} SIG 邀请您参加 {{start_time}} 召开的ZOOM会议(自动录制)</td>
            </tr>
            <tr>
                <td colspan="3" style="background-color: rgb(212, 207, 207); padding-left: 30px;">会议主题：{{topic}}</td>
            </tr>
            <tr>
                <td colspan="3" style="background-color: rgb(212, 207, 207); padding-left: 30px;">会议链接：{{join_url}}</td>
            </tr>
            <tr>
                <td colspan="3" style="background-color: rgb(212, 207, 207); padding-left: 30px;">温馨提醒：建议接入会议后修改参会人的姓名，也可以使用您在gitee.com的ID</td>
            </tr>
            <tr>
                <td colspan="3" style="background-color: rgb(212, 207, 207); padding-left: 30px;">更多资讯尽在：https://openeuler.org/zh/</td>
            </tr>
            <tr>
                <td colspan="3" height="30" style="background-color: rgb(212, 207, 207);"></td>
            </tr>
            <tr>
                <td colspan="3" style="background-color: rgb(212, 207, 207); padding-left: 30px;">Hello!</td>
            </tr>
            <tr>
                <td colspan="3"style="background-color: rgb(212, 207, 207); padding-left: 30px;">openEuler {{sig_name}} SIG invites you to attend the ZOOM conferencei(auto recording) will be held at {{start_time}},</td>
            </tr>
            <tr>
                <td colspan="3" style="background-color: rgb(212, 207, 207); padding-left: 30px;">Subject: {{topic}},</td>
            </tr>
            <tr>
                <td colspan="3" style="background-color: rgb(212, 207, 207); padding-left: 30px;">You can join the meeting at {{join_url}}</td>
            </tr>
            <tr>
                <td colspan="3" style="background-color: rgb(212, 207, 207); padding-left: 30px;">Note: You are advised to change the participant name after joining the conference or use your ID at gitee.com.</td>
            </tr>
            <tr>
                <td colspan="3" style="background-color: rgb(212, 207, 207); padding-left: 30px;">More information: https://openeuler.org/zh/</td>
            </tr>
            <tr>
                <td colspan="3" height="30" style="background-color: rgb(212, 207, 207)"></td>
            </tr>
            <tr>
                <td width="400" height="250"><a href="{{h1}}"><img src="cid:templates/images/activities/{{s1}}" height="250" width="400" alt="openEuler meetup" /></a></td>
                <td width="400" height="250"><a href="{{h2}}"><img src="cid:templates/images/activities/{{s2}}" height="250" width="400" alt="openEuler meetup" /></a></td>
                <td width="400" height="250"><a href="{{h3}}"><img src="cid:templates/images/activities/{{s3}}" height="250" width="400" alt="openEuler meetup" /></a></td>
            </tr>
            <tr>
                <td  colspan="3" width="1200"  height="150"><a href="https://openeuler.org/zh/"><img src="cid:templates/images/foot.png" height="150" width="1210" alt="https://openeuler.org/zh/"/></a></td>
            </tr>
        </table>
    </body>
    </html>
    """
    return html


def get_html_without_summary_without_recordings():
    html = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta http-equiv="X-UA-Compatible" content="IE=edge">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Document</title>
    </head>
    <body>
        <table style="background-color: rgb(212, 207, 207); border: 0;">
            <tr>
                <td colspan="3" height="50" style="background-color: #003CBA; text-align: center; color: white; font-size: 24px;">openEuler conference</td>
            </tr>
            <tr>
                <td colspan="3" height="20" style="background-color: rgb(212, 207, 207)"></td>
            </tr>
            <tr>
                <td colspan="3" style="background-color: rgb(212, 207, 207); padding-left: 30px;">您好！</td>
            </tr>
            <tr>
                <td colspan="3" style="background-color: rgb(212, 207, 207); padding-left: 30px;">openEuler {{sig_name}} SIG 邀请您参加 {{start_time}} 召开的ZOOM会议</td>
            </tr>
            <tr>
                <td colspan="3" style="background-color: rgb(212, 207, 207); padding-left: 30px;">会议主题：{{topic}}</td>
            </tr>
            <tr>
                <td colspan="3" style="background-color: rgb(212, 207, 207); padding-left: 30px;">会议链接：{{join_url}}</td>
            </tr>
            <tr>
                <td colspan="3" style="background-color: rgb(212, 207, 207); padding-left: 30px;">温馨提醒：建议接入会议后修改参会人的姓名，也可以使用您在gitee.com的ID</td>
            </tr>
            <tr>
                <td colspan="3" style="background-color: rgb(212, 207, 207); padding-left: 30px;">更多资讯尽在：https://openeuler.org/zh/</td>
            </tr>
            <tr>
                <td colspan="3" height="30" style="background-color: rgb(212, 207, 207);"></td>
            </tr>
            <tr>
                <td colspan="3" style="background-color: rgb(212, 207, 207); padding-left: 30px;">Hello!</td>
            </tr>
            <tr>
                <td colspan="3"style="background-color: rgb(212, 207, 207); padding-left: 30px;">openEuler {{sig_name}} SIG invites you to attend the ZOOM conference will be held at {{start_time}},</td>
            </tr>
            <tr>
                <td colspan="3" style="background-color: rgb(212, 207, 207); padding-left: 30px;">Subject: {{topic}},</td>
            </tr>
            <tr>
                <td colspan="3" style="background-color: rgb(212, 207, 207); padding-left: 30px;">You can join the meeting at {{join_url}}</td>
            </tr>
            <tr>
                <td colspan="3" style="background-color: rgb(212, 207, 207); padding-left: 30px;">Note: You are advised to change the participant name after joining the conference or use your ID at gitee.com.</td>
            </tr>
            <tr>
                <td colspan="3" style="background-color: rgb(212, 207, 207); padding-left: 30px;">More information: https://openeuler.org/zh/</td>
            </tr>
            <tr>
                <td colspan="3" height="30" style="background-color: rgb(212, 207, 207)"></td>
            </tr>
            <tr>
                <td width="400" height="250"><a href="{{h1}}"><img src="cid:templates/images/activities/{{s1}}" height="250" width="400" alt="openEuler meetup" /></a></td>
                <td width="400" height="250"><a href="{{h2}}"><img src="cid:templates/images/activities/{{s2}}" height="250" width="400" alt="openEuler meetup" /></a></td>
                <td width="400" height="250"><a href="{{h3}}"><img src="cid:templates/images/activities/{{s3}}" height="250" width="400" alt="openEuler meetup" /></a></td>
            </tr>
            <tr>
                <td  colspan="3" width="1200"  height="150"><a href="https://openeuler.org/zh/"><img src="cid:templates/images/foot.png" height="150" width="1210" alt="https://openeuler.org/zh/"/></a></td>
            </tr>
        </table>
    </body>
    </html>
    """
    return html
    

def get_txt_with_summary_with_recordings():
    text = """
    您好！
    {{sig_name}} SIG 邀请您参加 {{start_time}} 召开的ZOOM会议(自动录制)
    会议主题：{{topic}
    会议内容：{{summary}}
    会议链接：{{join_url}}
    温馨提醒：建议接入会议后修改参会人的姓名，也可以使用您在gitee.com的ID
    更多资讯尽在：https://openeuler.org/zh/
    

    Hello!
    openEuler {{sig_name}} SIG invites you to attend the ZOOM conference(auto recording) will be held at {{start_time}},
    The subject of the conference is {{topic}},
    Summary: {{summary}}
    You can join the meeting at {{join_url}}
    Note: You are advised to change the participant name after joining the conference or use your ID at gitee.com.
    More information: https://openeuler.org/zh/
    """
    return text


def get_txt_with_summary_without_recordings():
    text = """
    您好！
    {{sig_name}} SIG 邀请您参加 {{start_time}} 召开的ZOOM会议
    会议主题：{{topic}
    会议内容：{{summary}}
    会议链接：{{join_url}}
    温馨提醒：建议接入会议后修改参会人的姓名，也可以使用您在gitee.com的ID
    更多资讯尽在：https://openeuler.org/zh/


    Hello!
    openEuler {{sig_name}} SIG invites you to attend the ZOOM conference will be held at {{start_time}},
    The subject of the conference is {{topic}},
    Summary: {{summary}}
    You can join the meeting at {{join_url}}
    Note: You are advised to change the participant name after joining the conference or use your ID at gitee.com.
    More information: https://openeuler.org/zh/
    """
    return text


def get_txt_without_summary_with_recordings():
    text = """
    您好！
    {{sig_name}} SIG 邀请您参加 {{start_time}} 召开的ZOOM会议(自动录制)
    会议主题：{{topic}
    会议链接：{{join_url}}
    温馨提醒：建议接入会议后修改参会人的姓名，也可以使用您在gitee.com的ID
    更多资讯尽在：https://openeuler.org/zh/


    Hello!
    openEuler {{sig_name}} SIG invites you to attend the ZOOM conference(auto recording) will be held at {{start_time}},
    The subject of the conference is {{topic}},
    You can join the meeting at {{join_url}}
    Note: You are advised to change the participant name after joining the conference or use your ID at gitee.com.
    More information: https://openeuler.org/zh/
    """
    return text


def get_txt_without_summary_without_recordings():
    text = """
    您好！
    {{sig_name}} SIG 邀请您参加 {{start_time}} 召开的ZOOM会议
    会议主题：{{topic}
    会议链接：{{join_url}}
    温馨提醒：建议接入会议后修改参会人的姓名，也可以使用您在gitee.com的ID
    更多资讯尽在：https://openeuler.org/zh/


    Hello!
    openEuler {{sig_name}} SIG invites you to attend the ZOOM conference will be held at {{start_time}},
    The subject of the conference is {{topic}},
    You can join the meeting at {{join_url}}
    Note: You are advised to change the participant name after joining the conference or use your ID at gitee.com.
    More information: https://openeuler.org/zh/
    """
    return text
