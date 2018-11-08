import pygame
import sys
from random import randint
import os
import csv
from sina import sina_spider
import time

########首先定义各个颜色的RBG的数值#########

BLACK = 0, 0, 0
WHITE = 255, 255, 255
RED = 255, 0, 0
GREEN = 0, 255, 0
BLUE = 0, 0, 255
GREY = 211, 211, 211
DEEP_GREY = 40, 40, 40

###########################################

############动态显示相关参数的设置###########

AXIS_WIDTH = 960
AXIS_HEIGHT = 640
FADE_SPEED = 20
TEXT_TOP1_TIME = '热搜第一持续次数'
DATE_INTERVAL = 30          #数据帧的设置，每秒30帧
TOP_NUM = 20                #显示的数量
BAR_HEIGHT = AXIS_HEIGHT//(TOP_NUM*1.5) #每一个BAR的高度

###########################################

#颜色转换，这里替换掉RGB数值随机的办法来初始化颜色
def HSV2RGB(H, S, V):
    if S == 0:
        return V, V, V
    else:
        H /= 60
        i = int(H)
        f = H - i
        a = int(V * (1-S))
        b = int(V * (1-S*f))
        c = int(V * (1-S*(1-f)))
        if i == 0:
            return V, c, a
        elif i == 1:
            return b, V, a
        elif i == 2:
            return a, V, c
        elif i == 3:
            return a, b, V
        elif i == 4:
            return c, a, V
        elif i == 5:
            return V, a, b

#找出在list中name的索引值,如果找不见则返回-1
def find_name(list, name):
    for i in range(len(list)):
        if list[i].name == name:
            return i
    return -1


#柱状图图类
class bar:
    def __init__(self, name, type, value):
        self.name = name
        self.type = type
        self.value = value
        self.lastvalue = value  #上一次的数值，方便前后对比进行相关的修改
        #颜色RGB使用随机值
        self.color = HSV2RGB(randint(0, 255), 0.75, 230)
        self.lastwidth = 0      #上一次的宽度，实际上与lastvalue相关
        #m初始化的时候并不进行显示，update操作才对数据进行显示
        self.rank = TOP_NUM + 1
        #上一次的排名，方便进行比较，对数据显示进行相关的修改
        self.lastrank = TOP_NUM + 1
    '''
        获取柱条的位置
        位置信息有：顶端位置、宽度、数值、透明度、是否显示
        输入参数：step, max_value
        step：步长，
        max_value：一次数据中的最大值
        该函数的返回值为：top, width, value, alpha, show
        top：表示驻条顶端位置，计算公式为rank*BAR_HEIGHT*1.5
        width：表示柱条宽度，计算公式(value/max_value) * AXIS_WIDTH
        value：柱条对应的数值
        alpha：柱条透明度，取值为0或者255
        show：是否显示柱条，当其不能排到TOP_NUM的时候不显示
    '''
    def get_pos(self, step, max_value):
        if step == -1:
            top = int(self.rank * BAR_HEIGHT * 1.5)
            if self.rank <= TOP_NUM:
                alpha = 255
                show = True
            else:
                alpha = 0
                show = False
            value = self.value
            width = (value/max_value) * AXIS_WIDTH
            return top, width, value, alpha, show
        '''
            当位置发生变化的时候，需要计算相应的位移和平滑数字
        '''
        if self.rank != self.lastrank:
            start = self.lastrank * BAR_HEIGHT * 1.5
            end = self.rank * BAR_HEIGHT * 1.5
            top = int(start + (end-start)*(step/DATE_INTERVAL))
            #被挤出榜外
            if self.rank > 20 and self.lastrank <= 20:

                alpha = 255 * (1-step/DATE_INTERVAL)
                show = True
            #后来居上，挤上榜单
            elif self.rank <= 20 and self.lastrank > 20:

                alpha = 255 * (step/DATE_INTERVAL)
                show = True
            else:
                if self.rank <= 20:
                    alpha = 255
                    show = True
                else:
                    alpha = 0
                    show = False
        else:
            top = int(self.rank * BAR_HEIGHT * 1.5)
            if self.rank <= 20:
                alpha = 255
                show = True
            else:
                alpha = 0
                show = False
        start = self.lastvalue
        end = self.value
        value = start + (end-start)*(step/DATE_INTERVAL)
        start = self.lastwidth
        end = (end/max_value) * AXIS_WIDTH
        width = start + (end - start) * (step/DATE_INTERVAL)
        value = int(value)

        return top, width, value, alpha, show



'''
    这里把所有的bar进行封装成一个class，方便后续的操作
    data存储所有的数据
'''
class bar_list:
    def __init__(self, list):
        self.data = list
        self.data.sort(key=lambda x: x.value, reverse=True)
        for i in range(len(self.data)):
            self.data[i].lastrank = self.data[i].rank
            self.data[i].rank = i + 1

    def update(self, data, max_value):
        for each in data:
            temp = find_name(self.data, each['name'])
            if temp != -1:
                self.data[temp].lastvalue = self.data[temp].value
                self.data[temp].lastwidth = (self.data[temp].value/max_value) * AXIS_WIDTH
                self.data[temp].value = each['value']
            else:
                self.data.append(bar(each['name'], each['type'], each['value']))
        self.data.sort(key=lambda x: x.value, reverse=True)
        for i in range(len(self.data)):
            self.data[i].lastrank = self.data[i].rank
            self.data[i].rank = i + 1


'''
    数据单位的变化，根据数据所处的范围进行相应的单位变化
    方便在可视化图表中进行显示
'''
def numstr(num):
    if num >= 100000000:
        if num % 100000000 == 0:
            return '%s亿'%(num//100000000)
        else:
            return '%.2f亿'%(num/100000000)
    elif num >= 10000:
        if num % 10000 == 0:
            return '%s万'%(num//10000)
        else:
            return '%.2f万'%(num/10000)
    else:

        return str(num)


'''
    对整个可视化的图进行分析
    可以把最终绘制的结果分为以下4个部分
    1）顶部信息栏，显示第一名的信息，包括类型，名称，占据榜首的时间
    2）坐标轴部分，横向的坐标轴
    3）柱状图部分，用于显示柱状图和相对应的纵坐标轴信息，以及数据
    4）时间显示部分，放在右下角，用于显示当前的时间
    
    
    数据结构参考说明
    
    变量存储方式的选择：
    由于每次都是依据时间的变化而变化，所以这里使用字典的方式存储数据，key值为date，
    字典每一项的值为一个列表，列表由若干字典组成，key为name,type,value
'''


'''
    坐标轴的设置
    pygame.draw中函数的第一个参数总是一个surface，然后是颜色，再后会是一系列的坐标等。
    计算机里的坐标，(0，0)代表左上角。而返回值是一个Rect对象，包含了绘制的领域，
    max_value:最大值
    min_limit:最小界限
    is_zero:是否最左端为0，如果不进行指定，则默认为True
    min_value:最小值，当is_zero为True时生效
'''
def axis(max_value, min_limit, is_zero=True, min_value=0):
    surface = pygame.surface.Surface((AXIS_WIDTH+60, AXIS_HEIGHT+20))
    surface.fill(WHITE)
    font = pygame.font.SysFont('SimHei', 15)

    if is_zero:
        if max_value >= min_limit:
            #获取最大值有多少位，便于进行设置横坐标轴
            temp = len(str(int(max_value)))
            #这个循环是为了快速找到合适的坐标轴设置，
            #注意此时的坐标轴设置未必是最佳的
            for i in (1, 2, 5, 10):
                if 6 <= max_value//(i*10**(temp-2)) <= 15:
                    kd = i * 10 ** (temp-2)
                    num = max_value//kd
                    break
        else:
            temp = len(str(min_limit))
            for i in (1, 2, 5, 10):
                if 6 <= min_limit // (i * 10 ** (temp - 2)) <= 15:
                    kd = i * 10 ** (temp - 2)
                    num = min_limit // kd
                    break
        global lastk
        if lastk != None and lastk < kd:
            global fadev
            fadev = FADE_SPEED
        lastk = kd

        if fadev != 0:
            fadev -= 1

        if fadev != 0:
            if i == 5:
                fkd = 2*10**(temp-2)
            else:
                fkd = kd//2
            fnum = max_value//fkd

        if fadev != 0:
            for each in (x*fkd for x in range(fnum+1) if x*fkd not in (x*kd for x in range(num+1))):
                temp = (each/max_value)*AXIS_WIDTH + 25
                color = 255 - 127*(fadev/FADE_SPEED)
                color = color, color, color
                '''
                    原型：pygame.draw.aaline(Surface, color, startpos, endpos, blend=1): return Rect
                    用途：绘制一条平滑的（消除锯齿）直线段
                '''
                pygame.draw.aaline(surface, color, (temp, 0), (temp, AXIS_HEIGHT-30))
                tsur = font.render(numstr(each), True, color)
                tsur_r = tsur.get_rect()
                tsur_r.center = temp, AXIS_HEIGHT-15
                surface.blit(tsur, tsur_r)
        # max_value的宽度适中为AXIS_WIDTH 那么剩下来的刻度宽度就显而易见了
        for each in (x*kd for x in range(num+1)):

            temp = (each/max_value)*AXIS_WIDTH + 25
            pygame.draw.aaline(surface, GREY, (temp, 0), (temp, AXIS_HEIGHT-30))
            tsur = font.render(numstr(each), True, GREY)
            tsur_r = tsur.get_rect()
            tsur_r.center = temp, AXIS_HEIGHT-15
            surface.blit(tsur, tsur_r)

    return surface

#顶部信息的设置
def top_bar(m_type, m_name, m_time):
    surface = pygame.surface.Surface((AXIS_WIDTH+60, 60))
    surface.fill(WHITE)
    font = pygame.font.SysFont('SimHei', 30)

    tsur = font.render(m_type, True, DEEP_GREY)
    surface.blit(tsur, (25, 15))
    tsur = font.render(m_name, True, DEEP_GREY)
    surface.blit(tsur, (25+int(AXIS_WIDTH*0.3), 15))
    tsur = font.render(TEXT_TOP1_TIME+str(m_time), True, DEEP_GREY)
    tsur_r = tsur.get_rect()
    tsur_r.right = AXIS_WIDTH + 60
    tsur_r.top = 15
    surface.blit(tsur, tsur_r)
    return surface

#底部时间的设置
def bottom_date(dates):
    font = pygame.font.SysFont('SimHei', 30)
    tsur = font.render(dates, True, DEEP_GREY)
    return tsur


'''
    柱状图
    每个高度为AXIS_HEIGHT//30
    需要有以下要素：
    1、一次INTERVAL中平滑变化顶端显示的数值
    2、一次INTERVAL中平滑移动有变动排名的项目
'''
def bar_graph(surface, pos, data, step):
    #设置中文显示字体
    font = pygame.font.SysFont('SimHei', int(BAR_HEIGHT)-2)
    font2 = pygame.font.SysFont('SimHei', int(BAR_HEIGHT))
    #暂且设置成全局变量存储数据
    global store
    for each in store.data:
        top, width, value, alpha, show = each.get_pos(step, store.data[0].value)
        if show:
            '''
                原型：pygame.draw.rect(Surface, color, Rect, width=0): return Rect
                用途：在Surface上绘制矩形，第二个参数是线条（或填充）的颜色，第三个参数Rect的形式是((x, y), (width, height))，
                表示的是所绘制矩形的区域，其中第一个元组(x, y)表示的是该矩形左上角的坐标，
                第二个元组 (width, height)表示的是矩形的宽度和高度。width表示线条的粗细，单位为像素；默认值为0，表示填充矩形内部。
                此外，Surface.fill 同样可以用来绘制填充矩形。
            '''
            pygame.draw.rect(surface, each.color, (pos[0]+1, pos[1]+top-30, width, BAR_HEIGHT))
            # pygame.font.Font.render()  ——  在一个新 Surface 对象上绘制文本
            tsur = font.render(each.name, True, each.color)
            tsur_r = tsur.get_rect()
            tsur_r.right, tsur_r.top = pos[0]-5, pos[1]+top-30
            # pygame.Surface.blit()  —  将一个图像（Surface 对象）绘制到另一个图像上方
            surface.blit(tsur, tsur_r)

            tsur = font2.render(each.name, True, each.color)
            tsur_r = tsur.get_rect()
            tsur_r.right, tsur_r.bottom = pos[0] + width, pos[1] + top + BAR_HEIGHT-30
            make_bold(surface, tsur, tsur_r)

            tsur = font2.render(each.name, True, WHITE)
            surface.blit(tsur, tsur_r)

            tsur = font.render(str(value), True, each.color)
            surface.blit(tsur, (pos[0]+width+5, pos[1]+top-30))

def make_bold(surface, tsur, rect):
    x, y = rect.left, rect.top
    surface.blit(tsur, (x-1, y-1))
    surface.blit(tsur, (x-1, y))
    surface.blit(tsur, (x-1, y+1))
    surface.blit(tsur, (x, y-1))
    surface.blit(tsur, (x, y))
    surface.blit(tsur, (x, y+1))
    surface.blit(tsur, (x+1, y-1))
    surface.blit(tsur, (x+1, y))
    surface.blit(tsur, (x+1, y+1))



def data_visulization():
    # 文件路径：E:\PycharmProjects\ranking_visualization\example.csv
    # path = input('输入文件路径及文件名:\n')
    # path = 'E:\PycharmProjects\\ranking_visualization\example.csv'
    # path = 'E:\PycharmProjects\DataVisualization\sina.csv'
    #
    # while not os.path.exists(path):
    #     print('路径错误')
    #     path = input('请重新输入正确的文件路径及文件名')
    #
    # with open(path) as f:
    #     data = list(csv.reader(f))


    while True:
        time.sleep(20)
        data = sina_spider()
        spider_flag = True
        ranks = {}
        for each in data:
            date = each[3]
            if date in ranks:
                ranks[date].append({'name': each[0], 'type': each[1], 'value': int(each[2])})
            else:
                ranks[date] = [{'name': each[0], 'type': each[1], 'value': int(each[2])}]

        data = ranks

        store = bar_list([])
        # 按照日期对数据进行排序
        data_date = list(data)
        index = 0
        max_index = len(data_date)

        frame = -1
        temp = sorted(data[data_date[0]], key=lambda x: x['value'], reverse=True)
        # print(data)
        lastmaxv = temp[0]['value']
        store.update(data[data_date[0]], lastmaxv)
        top1 = 0
        lasttop1 = ''

        pygame.init()
        screen = pygame.display.set_mode((1280, 720))
        clock = pygame.time.Clock()
        while spider_flag:
            for event in pygame.event.get():
                if event.type == 'QUIT':
                    pygame.quit()
                    sys.exit()

            if index == -1:
                clock.tick(30)
                continue

            screen.fill(WHITE)

            frame += 1
            if frame == DATE_INTERVAL + 1 and index != -1:
                frame = 0
                index += 1

            if frame == 0:
                top1 += 1
                # store.update(data[data_date[index]], store.data[0].value)

                if index == max_index:
                    store.update(data[data_date[max_index - 1]], store.data[0].value)
                else:
                    store.update(data[data_date[index]], store.data[0].value)

            maxv = store.data[0].value
            maxv = int(lastmaxv + (maxv - lastmaxv) * (frame / DATE_INTERVAL))
            if frame == 30:
                lastmaxv = store.data[0].value
            temp = axis(maxv, 10)
            axistemp = temp.get_rect()
            axistemp.left, axistemp.top = 150, 80
            axistemp = axistemp.right, axistemp.bottom
            screen.blit(temp, (150, 80))

            if lasttop1 != store.data[0].name:
                lasttop1 = store.data[0].name
                top1 = 0
            ttpye, tname = store.data[0].type, lasttop1
            temp = top_bar(ttpye, tname, top1)
            screen.blit(temp, (150, 0))

            # temp = bottom_date(data_date[index])
            if index == max_index:
                temp = bottom_date(data_date[max_index - 1])
            else:
                temp = bottom_date(data_date[index])
            temp_r = temp.get_rect()
            temp_r.center = axistemp[0] - 35, 0
            temp_r.bottom = axistemp[1] - 30
            screen.blit(temp, temp_r)

            if index == max_index:
                bar_graph(screen, (175, 80), data[data_date[max_index - 1]], -1)
                index = 0
                spider_flag = False
            else:
                bar_graph(screen, (175, 80), data[data_date[index]], frame)
            # bar_graph(screen, (175, 80), data[data_date[index]], frame)

            pygame.display.flip()
            clock.tick(30)





store = bar_list([])
lastk = None
fadev = 0

if __name__ == '__main__':
    data_visulization()