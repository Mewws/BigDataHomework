import requests
import datetime
import csv
from lxml import etree
import os
import time

class Item(object):
    def __init__(self, name, itype, value, date):
        self.name = name[2:-2]
        self.itype = itype[2:-2]
        self.value = value[2:-2]
        self.date = date
    def store_2_csv(self, filename):
        try:
            out = open(filename, 'a', newline='')
        except Exception as e:
            print('文件打开时出现异常，异常信息为：' + e)
            return
        csv_writer = csv.writer(out, dialect='excel')
        csv_writer.writerow([self.name, self.itype, self.value, self.date])



def sina_spider():
    base_url = 'https://s.weibo.com/top/summary?cate=realtimehot'
    response = requests.get(url=base_url)
    response_tree = etree.HTML(response.text)
    # print(response.text)
    for i in range(1, 50):
        name = response_tree.xpath('//*[@id="pl_top_realtimehot"]/table/tbody/tr['+str(i+1)+']/td[1]/text()')
        itype = response_tree.xpath('//*[@id="pl_top_realtimehot"]/table/tbody/tr['+str(i+1)+']/td[2]/a/text()')
        value = response_tree.xpath('//*[@id="pl_top_realtimehot"]/table/tbody/tr['+str(i+1)+']/td[2]/span/text()')
        date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        item = Item(str(itype), str(itype), str(value), date)
        item.store_2_csv('sina.csv')
        # print(type(itype))
        # print(item.name)
        # print(item.itype)
        # print(item.value)
        # print(item.date)

if __name__ == '__main__':
    sina_spider()