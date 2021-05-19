def get_html_with_summary_with_recordings():
    html = """
    <!DOCTYPE html>
    <html lang="en">

    <head>
        <meta charset="UTF-8">
        <meta http-equiv="X-UA-Compatible" content="IE=edge">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Document</title>
        <style>
            @media screen and (min-width:80rem){
                .section{
                    width:80rem;
                }
            }
            @media screen and (max-width:80rem){
                .section{
                    width:100%;
                }
            }
            .recent_activities>div{
                margin:2px;
                border-radius:8px;
                overflow:hidden;
                cursor:pointer;
            }
        </style>
    </head>

    <body style="text-align: center;">
        <div class='section' style="display: inline-block; margin: auto">
            <div class='email_head' ,
                style="display: inline-block; height: 3rem; width: 100%; line-height:3rem;color:white; font-weight:bold; background-color: #003CBA; text-align: center;">
                openEuler conference
            </div>
            <br />
            <div class='email_body' , style="display: inline-block;  width: 100%; background-color: rgb(212, 207, 207);">
                <div style="padding-left: 2rem;" class='zh'>
                    <p>您好！</p>
                    <p>openEuler {{sig_name}} SIG 邀请您参加 {{start_time}} 召开的ZOOM会议(自动录制)</p>
                    <p>会议主题：{{topic}}</p>
                    <pre style="font-family: 'Microsoft YaHei',serif">会议内容：{{summary}}</pre>
                    <p>会议链接：<a href="{{join_url}}">{{join_url}}</a></p>
                    <p>更多资讯尽在：<a href="https://openeuler.org/zh/">https://openeuler.org/zh/</a></p>
                    <br />
                    <br />
                </div>
                <div style="padding-left: 2rem;" class='en'>
                    <p>Hello!</p>
                    <p>openEuler {{sig_name}} SIG invites you to attend the ZOOM conference(auto recording) will be held at {{start_time}},
                    </p>
                    <p>The subject of the conference is {{topic}},</p>
                    <pre style="font-family: 'Microsoft YaHei UI',serif">Summary: {{summary}}</pre>
                    <p>You can join the meeting at <a href="{{join_url}}">{{join_url}}</a>.</p>
                    <p><a href="https://openeuler.org/zh/">More information</a></p>
                    <br />
                    <br />
                </div>
                <div class='recent_activities' ,
                    style="display: flex; justify-content: space-between; width: 100%; height: 13.5rem">
                    <div style="display: inline-block; flex-grow:1; width: 1%">
                        <a href="{{h1}}"><img style="width:100%" src="cid:templates/images/activities/{{s1}}" height='100%'></a>
                    </div>
                    <div style="display: inline-block; flex-grow:1; width: 1%">
                        <a href="{{h2}}"><img style="width:100%" src="cid:templates/images/activities/{{s2}}" height='100%'></a>
                    </div>
                    <div style="display: inline-block; flex-grow:1; width: 1%">
                        <a href="{{h3}}"><img style="width:100%" src="cid:templates/images/activities/{{s3}}" height='100%'></a>
                    </div>
                </div>
                <div class='email_foot' , style="display: inline-block; height: 11.5rem; width: 100%;">
                    <a href="https://openeuler.org/zh/"><img src='cid:templates/images/foot.png' alt='' width="100%" height="100%" /></a>
                </div>
            </div>
        </div>
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
        <style>
            @media screen and (min-width:80rem){
                .section{
                    width:80rem;
                }
            }
            @media screen and (max-width:80rem){
                .section{
                    width:100%;
                }
            }
            .recent_activities>div{
                margin:2px;
                border-radius:8px;
                overflow:hidden;
                cursor:pointer;
            }
        </style>
    </head>

    <body style="text-align: center;">
        <div class='section' style="display: inline-block; margin: auto">
            <div class='email_head' ,
                style="display: inline-block; height: 3rem; width: 100%; line-height:3rem;color:white; font-weight:bold; background-color: #003CBA; text-align: center;">
                openEuler conference
            </div>
            <br />
            <div class='email_body' , style="display: inline-block;  width: 100%; background-color: rgb(212, 207, 207);">
                <div style="padding-left: 2rem;" class='zh'>
                    <p>您好！</p>
                    <p>openEuler {{sig_name}} SIG 邀请您参加 {{start_time}} 召开的ZOOM会议</p>
                    <p>会议主题：{{topic}}</p>
                    <pre style="font-family: 'Microsoft YaHei',serif">会议内容：{{summary}}</pre>
                    <p>会议链接：<a href="{{join_url}}">{{join_url}}</a></p>
                    <p>更多资讯尽在：<a href="https://openeuler.org/zh/">https://openeuler.org/zh/</a></p>
                    <br />
                    <br />
                </div>
                <div style="padding-left: 2rem;" class='en'>
                    <p>Hello!</p>
                    <p>openEuler {{sig_name}} SIG invites you to attend the ZOOM conference will be held at {{start_time}},
                    </p>
                    <p>The subject of the conference is {{topic}},</p>
                    <pre style="font-family: 'Microsoft YaHei UI',serif">Summary: {{summary}}</pre>
                    <p>You can join the meeting at <a href="{{join_url}}">{{join_url}}</a>.</p>
                    <p><a href="https://openeuler.org/zh/">More information</a></p>
                    <br />
                    <br />
                </div>
                <div class='recent_activities' ,
                    style="display: flex; justify-content: space-between; width: 100%; height: 13.5rem">
                    <div style="display: inline-block; flex-grow:1; width: 1%">
                        <a href="{{h1}}"><img style="width:100%" src="cid:templates/images/activities/{{s1}}" height='100%'></a>
                    </div>
                    <div style="display: inline-block; flex-grow:1; width: 1%">
                        <a href="{{h2}}"><img style="width:100%" src="cid:templates/images/activities/{{s2}}" height='100%'></a>
                    </div>
                    <div style="display: inline-block; flex-grow:1; width: 1%">
                        <a href="{{h3}}"><img style="width:100%" src="cid:templates/images/activities/{{s3}}" height='100%'></a>
                    </div>
                </div>
                <div class='email_foot' , style="display: inline-block; height: 11.5rem; width: 100%;">
                    <a href="https://openeuler.org/zh/"><img src='cid:templates/images/foot.png' alt='' width="100%" height="100%" /></a>
                </div>
            </div>
        </div>
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
        <style>
            @media screen and (min-width:80rem){
                .section{
                    width:80rem;
                }
            }
            @media screen and (max-width:80rem){
                .section{
                    width:100%;
                }
            }
            .recent_activities>div{
                margin:2px;
                border-radius:8px;
                overflow:hidden;
                cursor:pointer;
            }
        </style>
    </head>

    <body style="text-align: center;">
        <div class='section' style="display: inline-block; margin: auto">
            <div class='email_head' ,
                style="display: inline-block; height: 3rem; width: 100%; line-height:3rem;color:white; font-weight:bold; background-color: #003CBA; text-align: center;">
                openEuler conference
            </div>
            <br />
            <div class='email_body' , style="display: inline-block;  width: 100%; background-color: rgb(212, 207, 207);">
                <div style="padding-left: 2rem;" class='zh'>
                    <p>您好！</p>
                    <p>openEuler {{sig_name}} SIG 邀请您参加 {{start_time}} 召开的ZOOM会议(自动录制)</p>
                    <p>会议主题：{{topic}}</p>
                    <p>会议链接：<a href="{{join_url}}">{{join_url}}</a></p>
                    <p>更多资讯尽在：<a href="https://openeuler.org/zh/">https://openeuler.org/zh/</a></p>
                    <br />
                    <br />
                </div>
                <div style="padding-left: 2rem;" class='en'>
                    <p>Hello!</p>
                    <p>openEuler {{sig_name}} SIG invites you to attend the ZOOM conference(auto recording) will be held at {{start_time}},
                    </p>
                    <p>The subject of the conference is {{topic}},</p>
                    <p>You can join the meeting at <a href="{{join_url}}">{{join_url}}</a>.</p>
                    <p><a href="https://openeuler.org/zh/">More information</a></p>
                    <br />
                    <br />
                </div>
                <div class='recent_activities' ,
                    style="display: flex; justify-content: space-between; width: 100%; height: 13.5rem">
                    <div style="display: inline-block; flex-grow:1; width: 1%">
                        <a href="{{h1}}"><img style="width:100%" src="cid:templates/images/activities/{{s1}}" height='100%'></a>
                    </div>
                    <div style="display: inline-block; flex-grow:1; width: 1%">
                        <a href="{{h2}}"><img style="width:100%" src="cid:templates/images/activities/{{s2}}" height='100%'></a>
                    </div>
                    <div style="display: inline-block; flex-grow:1; width: 1%">
                        <a href="{{h3}}"><img style="width:100%" src="cid:templates/images/activities/{{s3}}" height='100%'></a>
                    </div>
                </div>
                <div class='email_foot' , style="display: inline-block; height: 11.5rem; width: 100%;">
                    <a href="https://openeuler.org/zh/"><img src='cid:templates/images/foot.png' alt='' width="100%" height="100%" /></a>
                </div>
            </div>
        </div>
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
        <style>
            @media screen and (min-width:80rem){
                .section{
                    width:80rem;
                }
            }
            @media screen and (max-width:80rem){
                .section{
                    width:100%;
                }
            }
            .recent_activities>div{
                margin:2px;
                border-radius:8px;
                overflow:hidden;
                cursor:pointer;
            }
        </style>
    </head>

    <body style="text-align: center;">
        <div class='section' style="display: inline-block; margin: auto">
            <div class='email_head' ,
                style="display: inline-block; height: 3rem; width: 100%; line-height:3rem;color:white; font-weight:bold; background-color: #003CBA; text-align: center;">
                openEuler conference
            </div>
            <br />
            <div class='email_body' , style="display: inline-block;  width: 100%; background-color: rgb(212, 207, 207);">
                <div style="padding-left: 2rem;" class='zh'>
                    <p>您好！</p>
                    <p>openEuler {{sig_name}} SIG 邀请您参加 {{start_time}} 召开的ZOOM会议</p>
                    <p>会议主题：{{topic}}</p>
                    <p>会议链接：<a href="{{join_url}}">{{join_url}}</a></p>
                    <p>更多资讯尽在：<a href="https://openeuler.org/zh/">https://openeuler.org/zh/</a></p>
                    <br />
                    <br />
                </div>
                <div style="padding-left: 2rem;" class='en'>
                    <p>Hello!</p>
                    <p>openEuler {{sig_name}} SIG invites you to attend the ZOOM conference will be held at {{start_time}},
                    </p>
                    <p>The subject of the conference is {{topic}},</p>
                    <p>You can join the meeting at <a href="{{join_url}}">{{join_url}}</a>.</p>
                    <p><a href="https://openeuler.org/zh/">More information</a></p>
                    <br />
                    <br />
                </div>
                <div class='recent_activities' ,
                    style="display: flex; justify-content: space-between; width: 100%; height: 13.5rem">
                    <div style="display: inline-block; flex-grow:1; width: 1%">
                        <a href="{{h1}}"><img style="width:100%" src="cid:templates/images/activities/{{s1}}" height='100%'></a>
                    </div>
                    <div style="display: inline-block; flex-grow:1; width: 1%">
                        <a href="{{h2}}"><img style="width:100%" src="cid:templates/images/activities/{{s2}}" height='100%'></a>
                    </div>
                    <div style="display: inline-block; flex-grow:1; width: 1%">
                        <a href="{{h3}}"><img style="width:100%" src="cid:templates/images/activities/{{s3}}" height='100%'></a>
                    </div>
                </div>
                <div class='email_foot' , style="display: inline-block; height: 11.5rem; width: 100%;">
                    <a href="https://openeuler.org/zh/"><img src='cid:templates/images/foot.png' alt='' width="100%" height="100%" /></a>
                </div>
            </div>
        </div>
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
