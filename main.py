"""
Created on Tue Sep 14 16:48:25 2021
@author: Roman_Galkin
"""
import datetime
from matplotlib import pyplot as plt
from matplotlib.dates import DateFormatter
import http.client
import mariadb
import sys
from bs4 import BeautifulSoup
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage

def ConnectDB():
    try:
        conn = mariadb.connect(
            user="test",
            password="8I7ArIqE85Ro",
            host="localhost",
            port=3306,
            database="db1", autocommit=True
        )
    except mariadb.Error as e:
        print(f"Error connecting to MariaDB Platform: {e}")
        sys.exit(1)
    return conn.cursor()

def InsertIntoDB(cur, P1):
    try:
        query = "INSERT INTO positions (itemArticle,itemName,itemPrice) VALUES (?, ?, ?)"
        value = (P1[0], P1[1], P1[2])
        cur.execute(query, value)
    except mariadb.Error as e:
        print(f"Error: {e}")

def UpdatePriceIntoDB(cur, P1):
    try:
        query = "UPDATE positions SET itemPrice = %d WHERE itemArticle = %d"
        value = (P1[2],P1[0])
        cur.execute(query, value)
    except mariadb.Error as e:
        print(f"Error: {e}")

def UpdatePriceIntoHistoryDB(cur, P1):
    try:
        query = "INSERT INTO history_price (itemArticle, Date, itemPrice) VALUES (?, ?, ?)"
        value = (P1[0],datetime.date.today(), P1[2])
        cur.execute(query, value)
    except mariadb.Error as e:
        print(f"Error: {e}")


def IsArticleExist(cur, P1):
    try:
        query = "SELECT COUNT(*) FROM positions WHERE itemArticle="+P1
        cur.execute(query)
    except mariadb.Error as e:
        print(f"Error: {e}")
    return cur.fetchone()[0]

def ExtractPrice(cur, P1):
    try:
        query = "SELECT itemPrice FROM positions WHERE itemArticle=" + P1
        cur.execute(query)
    except mariadb.Error as e:
        print(f"Error: {e}")
    return cur.fetchone()[0]

def ExtractAllData(P1):
    conn = http.client.HTTPSConnection("api.scrapingant.com")
    url = "/v2/general?url=https://www.vseinstrumenti.ru/search_main.php?what="+P1+"&x-api-key=2a50a1297ca1482aba04b619060a1595&proxy_country=RU&browser=true"
    conn.request("GET", url)
    res = conn.getresponse()
    data = res.read()
    #print(data.decode("utf-8"))
    soup = BeautifulSoup(data, 'lxml')
    try:
        itemName = soup.find("meta", property="og:title").get("content")
        itemPrice = soup.find(itemprop='price').get("content")
    except:
        itemPrice = soup.find('div', class_='current-price').text.replace("р.", "")
        itemPrice = itemPrice.replace(" ", "")
    return [P1, itemName, itemPrice]

def WriteALetter(OldPrice, P1):
    body = f'Предыдущая цена - {OldPrice}, новая цена - {P1[2]}<BR>'
    body += f'Ссылка - https://www.vseinstrumenti.ru/search_main.php?what={P1[0]}'
    body += f'<BR><img src="cid:image1"><br>'

    # Attach Image
    fp = open('price_draw.png', 'rb')  # Read image
    msgImage = MIMEImage(fp.read())
    fp.close()

    # Define the image's ID as referenced above
    msgImage.add_header('Content-ID', '<image1>')
    sent_from = 'virix83@gmail.com'
    to = 'virix83@gmail.com'
    gmail_user = 'virix83@gmail.com'
    gmail_password = 'bmiqdoxypekggixd'
    msg = MIMEMultipart('alternative')
    msg['Subject'] = f'{P1[1]}, Артикул {P1[0]}'
    msg['From'] = gmail_user
    msg['To'] = 'virix83@gmail.com'
    msg.attach(msgImage)
    msg.attach(MIMEText(body, 'html'))
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.ehlo()
        server.starttls()
        server.login(gmail_user, gmail_password)
        server.sendmail(sent_from, to, msg.as_string())
        server.close()
        print('Email sent!')
    except:
        print('Something went wrong...')

def PriceGraph(cur, P1):
    Price = []
    Date = []

    formatter = DateFormatter('%d.%m.%y')
    try:
        query = "SELECT ItemPrice, DATE FROM history_price WHERE ItemArticle = " +str(P1) +" ORDER BY DATE"
        cur.execute(query)
    except mariadb.Error as e:
        print(f"Error: {e}")
    rows = cur.fetchall()
    for row in rows:
        Price += [row[0]]
        Date += [row[1]]
    plt.style.use('ggplot')
    plt.bar(Date, Price, width=0.5)
    ax = plt.subplot()
    ax.xaxis.set_major_formatter(formatter)
    ax.xaxis.set_tick_params(rotation=30, labelsize=8)
    plt.ylabel("Цена")
    plt.xlabel("Дата")
    plt.savefig("price_draw.png",dpi=80)
    #plt.show()
    return cur.fetchone()

def main():
    Articles = ['15877750'] #, '15513457', '15538221', '16306109', '17459934', '15857594', '22554075', '20425450', '17504340', '16264903', '16264905', '16264906', '19643118', '21843010']
    cur = ConnectDB()
    for Article in Articles:
        print(f'{cur} - {Article}')
        P0=ExtractAllData(Article)
        if IsArticleExist(cur, Article) == 0:
            InsertIntoDB(cur, P0)
        else:
               if int(P0[2])!=int(ExtractPrice(cur, Article)):
                # Шлёи письмо со старой и новой ценой, а затем обновляем цену в базе
                PriceGraph(cur, P0[0])
                WriteALetter(ExtractPrice(cur, Article), P0)
                UpdatePriceIntoDB(cur, P0)
                UpdatePriceIntoHistoryDB(cur,P0)
    '''
    PriceGraph(cur,Articles[0])
    '''
    cur.close()

if __name__ == "__main__":
    main()