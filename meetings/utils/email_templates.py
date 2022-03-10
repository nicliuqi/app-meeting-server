def feedback_email_template(feedback_type, feedback_email, feedback_content):
    body = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title></title>
    </head>
    <body>
        <p>反馈类型：{0}</p>
        <p>反馈者邮箱：{1}</p>
        <p>反馈内容：{2}</p>
    </body>
    </html>
    """.format(feedback_type, feedback_email, feedback_content)
    return body


def reply_email_template():
    body = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title></title>
    </head>
    <body>
        <p>感谢您向我们提出的宝贵意见!</p>
    </body>
    </html>
    """
    return body


def applicants_info_template():
    body = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title></title>
    </head>
    <body>
        <p>详细内容请查看csv附件</p>
    </body>
    </html>
    """
    return body
