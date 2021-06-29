import yagmail
yag = yagmail.SMTP("aviationdata0")
contents = [
    "This is the body.",
]
yag.send('claywdavis1@gmail.com', 'Test', contents)
