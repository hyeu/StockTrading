import datetime
from PyQt5 import uic
from Kiwoom import *
from Saveditem import *
import time
import os
import re

TRADING_TIME = [[[8, 30], [15, 20]]]

form_class = uic.loadUiType("pystock.ui")[0]

file_changed = False
pr_list = {}
lr_list = {}


class MyWindow(QMainWindow, form_class):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.saveditem = Saveditem()

        self.kiwoom = Kiwoom()
        self.kiwoom.comm_connect()

        fname = "ongoing_list.txt"
        if not os.path.isfile(fname):
            f = open(fname, 'wt')
            f.close()

        # 선정 종목 리스트
        self.load_buy_sell_list()

        self.file_upload()
        self.currentTime = datetime.datetime.now()
        self.timer = QTimer(self)
        self.timer.start(1000)
        self.timer.timeout.connect(self.timeout)

        #실시간 현재가
        self.scrnum = 5000
        self.set_current()
        self.kiwoom.OnReceiveRealData.connect(self.kiwoom._receive_real_data)
        self.kiwoom.sig_cl.sig_.connect(self.stockgridview)

        accouns_num = int(self.kiwoom.get_login_info("ACCOUNT_CNT"))
        accounts = self.kiwoom.get_login_info("ACCNO")
        accounts_list = accounts.split(';')[0:accouns_num]

        self.comboBox.addItems(accounts_list)
        self.exe_save = 0
        self.pushButton.clicked.connect(self.save_ongoing)
        self.check_balance()
        self.check_chejan_balance()

        # 주문 들어가는 부분
        self.timer3 = QTimer(self)
        self.timer3.start(1000 * 10)
        self.timer3.timeout.connect(self.timeout3)


    # 화면번호
    def getnum(self):
        if self.scrnum < 9999:
            self.scrnum += 1
        else:
            self.scrnum = 5000
        return int(self.scrnum)

    #실시간 현재가 불러오기 위한 종목코드 수집
    def file_upload(self):
        # 오늘의 추천 파일만 확인
        f = open("buy_list.txt", 'rt')
        buy_list = f.readlines()
        f.close()

        self.ncode = []
        self.check_price = []
        for i in range(len(buy_list)):
            split_row_data = buy_list[i].split(' ')
            self.ncode.append(split_row_data[8])
            self.check_price.append(split_row_data[14])

    #실시간 설정
    def set_current(self):
        for i in range(0, len(self.ncode)):
            self.kiwoom._set_real_reg(self.getnum(), self.ncode[i], "9001;10", "0")


    def stockgridview(self):
        item_cnt = len(self.saveditem.item_view)
        self.scode_list = list(self.saveditem.item_view.keys())
        self.tableWidget_5.setRowCount(item_cnt)
        for i in range(item_cnt):
            for j in range(3):
                #print(self.savedstockitem.item_view[self.scode_list[i]][j])
                item = QTableWidgetItem(self.saveditem.item_view[self.scode_list[i]][j])
                item.setTextAlignment(Qt.AlignVCenter | Qt.AlignCenter)
                self.tableWidget_5.setItem(i, j, item)

    # 버튼으로 파일 저장
    def save_ongoing(self):
        self.exe_save = 1
        self.check_chejan_balance()

    # 거래시간 확인
    def is_trading_time(self):
        global special
        vals = []
        current_time = self.currentTime.time()
        for start, end in TRADING_TIME:
            # 수능날
            now = datetime.datetime.now()
            soo_day = datetime.datetime.today().weekday()
            soo = now.isocalendar()
            # 수능날
            if soo_day == 3 and soo[1] == 46:
                start_time = datetime.time(hour = 9, minute = start[1])
                end_time = datetime.time(hour=16, minute=end[1])
            # 새해 다음날
            elif now.month == 1 and now.day == 2:
                start_time = datetime.time(hour = 9, minute = start[1])
                end_time = datetime.time(hour = end[0], minute= end[1])
            else:
                start_time = datetime.time(hour=start[0], minute=start[1])
                end_time = datetime.time(hour=end[0], minute=end[1])

            if (current_time >= start_time and current_time <= end_time):
                vals.append(True)
            else:
                vals.append(False)
                pass
        if vals.count(True):
            return True
        else:
            return False

    def is_end_time(self):
        vals = []
        current_time = self.currentTime.time()
        for start, end in TRADING_TIME:
            now = datetime.datetime.now()
            soo_day = datetime.datetime.today().weekday()
            soo = now.isocalendar()
            # 수능날
            if now.month == 11 and soo_day == 3:
                if soo[1] == 46:
                    end_time = datetime.time(hour=16, minute=20)
            # 새해 다음날
            elif now.month == 1 and now.day == 2:
                end_time = datetime.time(hour=15, minute=20)
            else:
                end_time = datetime.time(hour=end[0], minute=end[1])

            if (current_time == end_time):
                vals.append(True)
            else:
                vals.append(False)
                pass
        if vals.count(True):
            return True
        else:
            return False

    # 자동 주문
    def trade_stocks(self):
        auto_buy = []
        hoga_lookup = {'지정가': "00", '시장가': "03"}

        global lr_list
        global pr_list

        current_time = datetime.datetime.now()

        f = open("buy_list.txt", 'rt')
        buy_list = f.readlines()
        auto_buy += buy_list
        f.close()

        account = self.comboBox.currentText()

        now = datetime.datetime.now()
        soo_day = datetime.datetime.today().weekday()
        soo = now.isocalendar()
        today_hd = datetime.datetime.today().strftime("%Y%m%d")

        # 매수
        for i in range(len(buy_list)):
            split_row_data = buy_list[i].split(' ')
            code = split_row_data[8]
            num = split_row_data[13]
            price = split_row_data[14]
            hoga = "지정가"

            if self.is_trading_time()==True:
                if code in self.scode_list:
                    if int(price) > 0 and int(price) <= int(self.saveditem.item_view[code][1]):
                        print("{0}: 코드, {1}: 주문가격 {2}: 현재가".format(code, int(price), int(self.saveditem.item_view[code][1])))
                        self.kiwoom.send_order("send_order_req", "0101", account, 1, code, int(num), int(price),
                                           hoga_lookup[hoga], "")
                        buy_list[i] = buy_list[i].replace(price, "-1")

            """elif self.is_trading_time() == False:
                self.kiwoom.send_order("send_order_req", "0101", account, 1, code, int(num), int(price),
                                       hoga_lookup[hoga], "")
                buy_list[i] = buy_list[i].replace(split_row_data[14], "-1")"""

            f = open("buy_list.txt", 'wt')
            for row_data in buy_list:
                f.write(row_data)

        # 매도
        num_data = len(self.kiwoom.opw00018_output['multi'])

        for i in range(num_data):
            code_name = self.kiwoom.opw00018_output['compare'][i][0]
            quantity = self.kiwoom.opw00018_output['compare'][i][1]
            current_price = self.kiwoom.opw00018_output['compare'][i][2]
            purchase_price = self.kiwoom.opw00018_output['compare'][i][3]
            print("종목이름: %s, 현재가격: %s, 구입가격: %s" % (code_name, current_price, purchase_price))

            location = 0
            while (location < len(current_price)):
                if current_price[location] == ',':
                    current_price = current_price[:location] + current_price[location + 1::]
                location += 1
            current_price = int(current_price)

            location2 = 0
            while (location2 < len(purchase_price)):
                if purchase_price[location2] == ',':
                    purchase_price = purchase_price[:location2] + purchase_price[location2 + 1::]
                location2 += 1

            for j in range(len(buy_list)):
                split_row_data = buy_list[j].split(' ')
                hd = split_row_data[7]
                code = split_row_data[8]
                num = split_row_data[13]
                price = split_row_data[14]
                pr = split_row_data[15]
                lr = split_row_data[16].replace("\n", "")
                hoga = "지정가"

                code_new = self.kiwoom.get_master_code_name(code)

                due_time = current_time.replace(hour=15, minute=15, second=0, microsecond=0)
                if soo_day == 3 and soo[1] == 46:
                    due_time = current_time.replace(hour=16, minute=15, second=0, microsecond=0)

                if due_time < current_time and price == "-1":
                    print(hd, today_hd)
                    if hd == today_hd:
                        self.kiwoom.send_order("send_order_req", "0101", account, 2, code, num, current_price,
                                               hoga_lookup[hoga], "")
                        print("hd 만료, 시장가 판매")

                #if code_name == code_new and int(quantity) >= int(num): << 에러남 확인 바람
                if code_name == code_new:
                    print("code name: %s, lr: %f, pr: %f" % (code, float(lr), float(pr)))
                    pr_price = float(pr) * int(purchase_price)
                    print("pr_price: %f * %d = %d" % (float(pr), int(purchase_price), int(pr_price)))
                    lr_price = float(lr) * float(purchase_price)
                    pr_price = int(pr_price)
                    lr_price = int(lr_price)
                    lr_list[code_name] = lr_price
                    pr_list[code_name] = pr_price
                    print("profit rate price: ", pr_price)
                    print("loss rate price: ", lr_price)
                    print("current price: ", current_price)

                    if price == "-1" and self.is_trading_time() == True:

                        if (current_price >= pr_price):
                            self.kiwoom.send_order("send_order_req", "0101", account, 2, code, num, current_price,
                                                   hoga_lookup[hoga], "")
                            print("pr 주문완료")
                            print(account, code, num, current_price, hoga_lookup[hoga])
                            buy_list[j] = buy_list[j].replace(split_row_data[14], "-2")
                            break


                        elif current_price <= lr_price:
                            self.kiwoom.send_order("send_order_req", "0101", account, 2, code, num, current_price,
                                                   hoga_lookup[hoga], "")
                            print(account, code, num, current_price, hoga_lookup[hoga])
                            buy_list[j] = buy_list[j].replace(split_row_data[14], "-2")
        print(lr_list)
        print(pr_list)

        # file update
        f = open("buy_list.txt", 'wt')
        for row_data in buy_list:
            f.write(row_data)
        f.close()

    def load_buy_sell_list(self):

        global file_changed

        current_time = datetime.datetime.now()
        today_file = datetime.datetime.today().strftime("%Y%m%d")

        file_name = today_file +"추천.txt"
        print(file_name)

        if os.path.isfile(file_name) == False:
            print("오늘의 추천 파일을 찾을 수 없습니다.")


        elif file_changed == False and current_time < current_time.replace(hour=8, minute=30):
            print(file_name, " buy_list로 변환")
            f = open(file_name, 'rt')
            temp_list = f.readlines()
            f.close()

            frow_data = []
            for row_data in temp_list:
                frow_data.append(' '.join(row_data.split()))
            frow_data = filter(str.strip, frow_data)
            temp = []
            for x in frow_data:
                temp.append(x)

            bl = []
            for j in range(2, len(temp) - 1):
                x = []
                split_row_data = temp[j].split(' ')
                split_row_data[7] = (split_row_data[7][split_row_data[7].find("(") + 1:split_row_data[7].find(")")])
                split_row_data[8] = re.sub(r'\([^)]*\)', '', split_row_data[8])
                split_row_data[9] = split_row_data[9].replace("원", "")
                split_row_data[9] = split_row_data[9].replace(",", "")
                split_row_data[13] = split_row_data[13].replace("주", "")
                split_row_data[13] = split_row_data[13].replace(",", "")
                split_row_data[14] = split_row_data[14].replace("원", "")
                split_row_data[14] = int(split_row_data[14].replace(",", ""))

                for i in range(len(split_row_data)):
                    x.append(split_row_data[i])
                x = map(str, x)
                y = " ".join(x)
                bl.append(y)

            # 전날 미매도 파일 불러오기
            f = open("ongoing_list.txt", 'rt')
            sell_list = f.readlines()
            sell_list2 = [s.rstrip() for s in sell_list]
            bl += sell_list2
            f.close()

            f = open("buy_list.txt", 'wt')
            for i in range(len(bl)):
               # print(bl[i])
                f.write(bl[i])
                f.write("\n")
            f.close()

            file_changed = True
            print("file_changed?? ", file_changed)

        f = open("buy_list.txt", 'rt')
        buy_list = f.readlines()
        f.close()

        row_count = len(buy_list)
        self.tableWidget_3.setRowCount(row_count)

        self.num_name = {}
        # buy list
        # j:행, i:열
        for j in range(len(buy_list)):
            split_row_data = buy_list[j].split(' ')
            temp_name = split_row_data[8]
            # 종목명 구하기
            code_name = self.kiwoom.get_master_code_name(temp_name)
            self.num_name[code_name] = temp_name

            for i in range(len(split_row_data)):
                item = QTableWidgetItem(split_row_data[i].rstrip())
                item.setTextAlignment(Qt.AlignVCenter | Qt.AlignCenter)
                self.tableWidget_3.setItem(j, i, item)

        self.tableWidget_3.resizeRowsToContents()
        print("num_name", self.num_name)

    def timeout(self):
        # market_start_time = QTime(9, 0, 0)
        current_time = QTime.currentTime()
        """if current_time > market_start_time and self.trade_stocks_done is False:
            self.trade_stocks()
            self.trade_stocks_done = True"""
        now = QDate.currentDate()
        text_time = now.toString(Qt.DefaultLocaleLongDate) + " " + current_time.toString("hh:mm:ss")
        time_msg = text_time

        state = self.kiwoom.get_connect_state()
        if state == 1:
            state_msg = "서버 연결 중"
        else:
            state_msg = "서버 미 연결 중"

        self.statusbar.showMessage(state_msg + " | " + time_msg)

    def timeout3(self):
        print(datetime.datetime.now())
        self.trade_stocks()
        print("trade_stocks 완료")
        self.check_balance()
        print("check_balance 완료")
        self.check_chejan_balance()
        print("check_chejan_balance 완료")
        self.load_buy_sell_list()
        print("load_buy_sell_list 완료")

    def check_chejan_balance(self):
        f = open("buy_list.txt", 'rt')
        buy_list = f.readlines()
        f.close()

        name = []
        num_order = []
        file_price = []
        buy_list2 = []

        for i in range(len(buy_list)):
            split_row_data = buy_list[i].split(' ')
            code = split_row_data[8]
            num = split_row_data[13]
            price = int(split_row_data[14])
            name.append(code)
            num_order.append(num)
            file_price.append(price)
        # SetInputValue(입력 데이터 설정)과 CommRqData(TR 요청)
        # 최대 20개의 보유 종목 데이터 리턴 반복
        self.kiwoom.reset_opt10075_output()
        account_number = self.kiwoom.get_login_info("ACCNO")
        account_number = account_number.split(';')[0]

        self.kiwoom.set_input_value("계좌번호", account_number)
        self.kiwoom.comm_rq_data("opt10075_req", "opt10075", 0, "2000")

        while self.kiwoom.remained_data:
            time.sleep(0.2)
            self.kiwoom.set_input_value("계좌번호", account_number)
            self.kiwoom.comm_rq_data("opt10075_req", "opt10075", 0, "2000")
            # if self.is_trading_time() == False:
            #    break

        item_count = len(self.kiwoom.opt10075_output['no_che'])
        self.tableWidget_4.setRowCount(item_count)

        for j in range(item_count):
            row = self.kiwoom.opt10075_output['no_che'][j]
            for i in range(len(row)):
                item = QTableWidgetItem(row[i])
                item.setTextAlignment(Qt.AlignVCenter | Qt.AlignRight)
                self.tableWidget_4.setItem(j, i, item)
                if self.is_end_time() == True or self.is_trading_time() == False or self.exe_save == 1:
                    if row[0] == '체결':
                        # print(self.kiwoom.opt10075_output['no_che'][j])
                        # 오늘자 파일의 매수 확인 후 ongoing_list에 저장
                        if row[1] == '+매수':
                            # if row[1] == '-매도':
                            for l in range(0, j + 1):
                                if self.kiwoom.opt10075_output['no_che'][l][3] == \
                                        self.kiwoom.opt10075_output['no_che'][j][3]:
                                    # print("l-{0} {1}".format(l, self.kiwoom.opt10075_output['no_che'][l]))
                                    # print("j-{0} {1}".format(j, self.kiwoom.opt10075_output['no_che'][j]))
                                    # 후에 매도가 됐는지 확인
                                    if not self.kiwoom.opt10075_output['no_che'][l][1] == '-매도':
                                        for k in range(len(buy_list)):
                                            """print(k)
                                            print("{0} {1}".format(int(self.kiwoom.opt10075_output['no_che'][j][4]), int(self.kiwoom.opt10075_output['no_che'][j][7])))
                                            print("{0} {1}".format(int(num_order[k]), int(self.check_price[k])))
                                            print("-----")"""
                                            if int(self.num_name[self.kiwoom.opt10075_output['no_che'][j][3]]) == int(name[k]) \
                                                    and int(self.kiwoom.opt10075_output['no_che'][j][4]) == int(num_order[k])\
                                                    and int(self.kiwoom.opt10075_output['no_che'][j][7]) == int(self.check_price[k]):
                                                #print(buy_list[k])
                                                #buy_list[k].replace(self.check_price[k], '-1')
                                                buy_list2.append(buy_list[k])
                        # 계속 감시 중인 종목이 매도되지 않을 시 ongoing_list에 추가
                        elif row[1] == '-매도':
                            for s in range(len(buy_list)):
                                if file_price[s] == -1:
                                    if not int(self.num_name[self.kiwoom.opt10075_output['no_che'][j][3]]) == int(name[s]) \
                                        and int(self.kiwoom.opt10075_output['no_che'][j][4]) == int(num_order[s]):
                                        buy_list2.append(buy_list[s])


                                # print(self.kiwoom.opt10075_output['no_che'][j][3])
                                # print("l - %d, j - %d" %(l, j))
                                # print("확인용", self.kiwoom.opt10075_output['no_che'][l])
                            """for k in range(len(buy_list)):
                                if int(self.num_name[row[3]]) == int(name[k]):
                                    #print(k)
                                    #print(buy_list[k])
                                    buy_list2.append(buy_list[k])"""
        buy_list2 = list(set(buy_list2))
        if self.is_end_time() == True or self.is_trading_time() == False or self.exe_save == 1:
            f = open("ongoing_list.txt", 'wt')
            for row_data in buy_list2:
                row_data = row_data
                f.write(row_data)
            f.close()

        self.exe_save == 0
        self.tableWidget_4.resizeRowsToContents()

    # 잔고 및 보유 계좌 정보 확인
    def check_balance(self):
        self.kiwoom.reset_opw00018_output()
        account_number = self.kiwoom.get_login_info("ACCNO")
        account_number = account_number.split(';')[0]
        self.kiwoom.set_input_value("계좌번호", account_number)
        self.kiwoom.comm_rq_data("opw00018_req", "opw00018", 0, "2000")
        while self.kiwoom.remained_data:
            time.sleep(0.2)
            self.kiwoom.set_input_value("계좌번호", account_number)
            self.kiwoom.comm_rq_data("opw00018_req", "opw00018", 2, "2000")
        # opw00001
        # 예수금 데이터 얻어오기
        self.kiwoom.set_input_value("계좌번호", account_number)
        #모의투자 시 밑의 세줄 주석 처리
        #self.kiwoom.set_input_value("비밀번호", "0000")
        #self.kiwoom.set_input_value("비밀번호입력매체구분", "00")
        #self.kiwoom.set_input_value("조회구분", 1)
        self.kiwoom.comm_rq_data("opw00001_req", "opw00001", 0, "2000")

        # balance
        # 예수금 데이터 tableWidget에 출력
        item = QTableWidgetItem(self.kiwoom.d2_deposit)
        item.setTextAlignment(Qt.AlignVCenter | Qt.AlignRight)
        self.tableWidget.setItem(0, 0, item)

        # 해당 칼럼에 값 추가
        for i in range(1, 6):
            item = QTableWidgetItem(self.kiwoom.opw00018_output['single'][i - 1])
            item.setTextAlignment(Qt.AlignVCenter | Qt.AlignRight)
            self.tableWidget.setItem(0, i, item)
        # 아이템 크기에 맞춰 행 높이 조절
        self.tableWidget.resizeRowsToContents()
        # Item list 보유종목 출력
        item_count = len(self.kiwoom.opw00018_output['multi'])
        self.tableWidget_2.setRowCount(item_count)
        for j in range(item_count):
            row = self.kiwoom.opw00018_output['multi'][j]
            if row[0] in lr_list and pr_list:
                str_lr = str(lr_list[row[0]])
                row[4] = str_lr
                print(row[4])
                str_pr = str(pr_list[row[0]])
                row[5] = str_pr
                print(row[5])
            print(row)
            for i in range(len(row)):
                item = QTableWidgetItem(row[i])
                item.setTextAlignment(Qt.AlignVCenter | Qt.AlignRight)
                self.tableWidget_2.setItem(j, i, item)
        self.tableWidget_2.resizeRowsToContents()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    myWindow = MyWindow()
    myWindow.show()
    app.exec_()