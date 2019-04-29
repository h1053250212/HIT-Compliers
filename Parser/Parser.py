from Grammar import *
from Lexer import *
import time

class Parser():
    """ LR1语法分析器 """
    def __init__(self):
        self.start_symbol = ''
        self.productions = []
        self.first_set = {}
        self.followSet = {}
        self.terminals = []
        self.nonterminals = []
        self.automata = []
        self.table = []
        self.actionTable = []
        self.gotoTable = []

    def build_automata(self):
        """
        Build the automata for recognizing the viable prefix.

        Parameters:
          self - a parser obejct

        """
        start_state = [Item(self.start_symbol + "'", ['.', self.start_symbol], '#')]
        automata = [self.closure(start_state)]
        flag = True
        while flag:
            flag = False
            for state in automata:
                for symbol in self.nonterminals + self.terminals:
                    new_set = self.goto(state, symbol)
                    if len(new_set) == 0:      # the state goes nowhere with the symbol
                        continue
                    if new_set not in automata:
                        automata.append(new_set)
                        flag = True
        self.automata = automata

    def closure(self, itemset):
        """
        Build the closure of the given state, or say item set.

        Args:
            itemset: a state of the automata, which holds some items

        Returns:
            itemset: an expanded item set, or say its closure
        """
        for item in itemset:
            right = item.right
            index = right.index('.')
            vars = len(right) - index - 1            # number of symbols after dot
            if vars == 0:
                continue
            symbol = right[index + 1]               # the first symbol after dot
            for p in self.productions:
                if p.left == symbol:
                    # build a new item and calculate its lookahead symbol
                    # construct the right part by moving the dot one step backward
                    # two conditions for calculating the lookahead symbol
                    # if there is only one symbol after dot, the new lookahead inherits from
                    # the original item;
                    # otherwise, the new lookahead will be the first set of the right part of after dot
                    # e.g. for A -> B.CDEF, C -> GH
                    # new item: C -> .GH, lookahead(C) = first(DEF)
                    if vars == 1:           # only one symbol after dot
                        lookahead = item.lookahead
                        if type(lookahead) is not list:
                            lookahead = [lookahead]
                    else:
                        lookahead = []
                        flag = True         # records whether all the symbols after dot are nullable
                        for v in range(index + 2, index + vars + 1):
                            sym = right[v]
                            first = self.first_set[sym]
                            for terminal in first:
                                if terminal not in lookahead and terminal != '$':
                                    lookahead.append(terminal)
                            if '$' not in first:
                                flag = False
                                break
                        if flag is True:    # then '#' could be met
                            lookahead.append('#')
                    new_right = ['.'] + p.right
                    for terminal in lookahead:
                        new_item = Item(p.left, new_right, terminal)
                        if new_item not in itemset:
                            itemset.append(new_item)

        return itemset

    def goto(self, itemset, symbol):        # 求出给定项目集对于符号X的转移状态
        """
        Construct the transition state.

        Args:
            itemset: a state of the automata, which holds some items
            symbol: the transfer symbol
        Returns:
            itemset: a transition state
        """
        new_state = []
        for item in itemset:
            right = item.right
            index = right.index('.')
            if index == len(right) - 1 or right[1] == '$':  # no symbol follows the dot or epsilon transition
                continue
            if right[index + 1] == symbol:
                new_right = right.copy()
                new_right[index], new_right[index + 1] = new_right[index + 1], new_right[index]
                new_item = Item(item.left, new_right, item.lookahead)
                new_state.append(new_item)
        new_state = self.closure(new_state)
        return new_state

    def buildTable(self):
        """
        Construct the action table and goto table.

        Args:
            self: a parser object
        """
        action_table, goto_table = [], []
        terms = self.terminals + ['#']
        for i in range(len(self.automata)):
            for symbol in terms:                    # fill the action table
                shiftable = []                      # collect the lookahead symbols of reducible items
                for item in self.automata[i]:
                    right = item.right
                    index = right.index('.')

                    if index == len(right) - 1:     # a reducible item, fill with reduce action
                        if symbol == item.lookahead and item.left != self.start_symbol + "'":          # 纵坐标终结符恰好为展望符，归约
                            right = item.right.copy()
                            right.pop(right.index('.'))
                            pindex = self.production_index(item.left, right)
                            entry = Entry(i, symbol, 'r' + str(int(pindex) + 1))
                            if not self.contains(action_table, entry):
                                action_table.append(entry)

                        if item.left == self.start_symbol + "'":    # initial state, accept it
                            entry = Entry(i, '#', 'acc')
                            if not self.contains(action_table, entry):
                                action_table.append(entry)
                        continue

                    if right[index + 1] == '$' and symbol == item.lookahead:
                        right = item.right.copy()
                        right.pop(right.index('.'))
                        pindex = self.production_index(item.left, right)
                        entry = Entry(i, symbol, 'r' + str(pindex + 1))
                        if not self.contains(action_table, entry):
                            action_table.append(entry)
                        continue

                    if right[index + 1] == symbol and right[index + 1] != '$':   # 如果点后紧跟着纵坐标对应的终结符
                        shiftable.append(right[index + 1])

                if len(shiftable) != 0:
                    gotoState = self.goto(self.automata[i], symbol)
                    gotoIndex = self.stateIndex(gotoState)      # shift后应进入的状态
                    entry = Entry(i, symbol, 's' + str(gotoIndex))
                    if not self.contains(action_table, entry):
                        action_table.append(entry)

            # 填goto表
            for symbol in self.nonterminals:
                gotoState = self.goto(self.automata[i], symbol)
                gotoIndex = self.stateIndex(gotoState)
                if gotoIndex != None:
                    entry = Entry(i, symbol, gotoIndex)
                    goto_table.append(entry)
        self.actionTable = action_table
        self.gotoTable = goto_table

    def outputTable(self):
        f = open('ActionTable.txt', 'w')
        for entry in self.actionTable:
            string = str(entry.state) + "\t" + str(entry.symbol) +\
                     "\t" + str(entry.content) + "\n"
            f.write(string)
        f.close()
        f = open('GotoTable.txt', 'w')
        for entry in self.gotoTable:
            string = str(entry.state) + "\t" + str(entry.symbol) +\
                     "\t" + str(entry.content) + "\n"
            f.write(string)
        f.close()

    def readTable(self):
        actionTable, gotoTable = [], []
        for line in open('ActionTable.txt', 'r'):
            l = line.split()
            state, symbol, content = l[0], l[1], l[2]
            entry = Entry(state, symbol, content)
            actionTable.append(entry)
        for line in open('GotoTable.txt', 'r'):
            l = line.split()
            state, symbol, content = l[0], l[1], l[2]
            entry = Entry(state, symbol, content)
            gotoTable.append(entry)
        self.actionTable = actionTable
        self.gotoTable = gotoTable

    def findAction(self, state, symbol):
        for entry in self.actionTable:
            if int(entry.state) == state and entry.symbol == symbol:
                return entry.content

    def findGoto(self, state, symbol):
        for entry in self.gotoTable:
            if int(entry.state) == state and entry.symbol == symbol:
                return int(entry.content)

    def parse(self, w):
        f = open('Analysis_Result.txt','w')
        stateStack, symbolStack = [0], ['#']
        w.append(['#', '-', '-'])
        i = 0
        step = 0
        while True:
            symbol = w[i][0]
            type = w[i][1]
            if type == 'digit' or type == 'IDN':
                symbol = w[i][1]
            elif type == 'delimiter' or type == 'OP':
                symbol = w[i][0]
            f.write("Read symbol\t" + str(symbol) + '\n')
            top = stateStack[-1]
            content = self.findAction(top, symbol)
            if content == None:
                print("Error at line", w[i][3], "no action")
                f.write("Error at line\t" + str(w[0][3]) + "\tno action\n")
                break
            if content[0] == 's':
                stateIndex = int(content[1:])
                stateStack.append(stateIndex)
                symbolStack.append(symbol)
                f.write("\t\tshift\t" + str(symbol) + "\tand push state\t" + str(stateIndex) + "\n")
                i += 1
                if i == len(w):
                    # 保持输入字符串的最右端是$，如果不够就给它补！
                    w.append(['$', '-', '-'])
            elif content[0] == 'r':
                # 从状态栈中弹出|β|个符号
                pindex = int(content[1:])
                p = self.productions[pindex - 1]
                length = len(p.right)
                stateStack = stateStack[0:len(stateStack) - length]

                # 归约式左部替换符号栈的栈顶
                symbolStack = symbolStack[0:len(symbolStack) - length]
                symbolStack.append(p.left)

                f.write("\t\treduce using the production\t" + str(p.left) +"\t"+ str(p.right) + "\n")
                # 将goto的状态压入状态栈
                state = self.findGoto(stateStack[-1], p.left)
                f.write("\t\tpush state\t" + str(state) + "\n")
                stateStack.append(state)

            elif content == 'acc':
                print("Accept! Congratulations!")
                f.write("Accept! Congratulations!\n")
                break
            else:
                print("error: no choice")
                f.write("error: no choice\n")

            f.write("\t\tState stack:\t" + str(stateStack) + "\n")
            f.write("\t\tSymbol stack:\t" + str(symbolStack) + "\n")
            # self.restInput(w, i + 1)
            step += 1
        print("Finished in", step, "steps")
        f.write("Finished in\t" + str(step) + "\tsteps\n")

    def restInput(self, w, index):
        print("\t\tThe rest of input string:\t", end="")
        for i in range(index, len(w)):
            print(w[i][0]+"\t", end="")
        print()

    def contains(self, tab, entry):
        for each in tab:
            if each.state == entry.state and each.symbol == entry.symbol \
                    and each.content == entry.content:
                return True
        return False

    def production_index(self, left, right):
        for p in self.productions:
            if p.left == left and p.right == right:
                return p.index

    def stateIndex(self, state):
        for i in range(len(self.automata)):
            cur = self.automata[i]                    # 类中存放的第i个状态
            if len(cur) != len(state):  # 给定状态
                continue
            flag = True
            for j in range(len(cur)):         # 每个item必须相同
                if cur[j] == state[j]:
                    continue
                else:
                    flag = False
                    break
            if flag:
                return i

    def viewSet(self, itemset):         # 查看一个项目集下的所有项目
        for item in itemset.items:
            print(item.left, item.right, item.lookahead)

    def viewItem(self, item):
        print(item.left, item.right, item.lookahead)

    def viewStates(self, states):       # 查看自动机的所有状态，显示其蕴含的项目
        i = 0
        for state in states:
            print(i)
            self.viewSet(state)
            i += 1

    def viewTable(self):
        print("Action table:")
        for entry in self.actionTable:
            print(entry.state, entry.symbol, entry.content)
        print("Goto table:")
        for entry in self.gotoTable:
            print(entry.state, entry.symbol, entry.content)

    def configure(self, grammar):
        self.productions = grammar.productions
        self.start_symbol = grammar.startSym
        self.nonterminals = grammar.nonterminals
        self.terminals = grammar.terminals
        self.first_set = grammar.firstSet
        self.followSet = grammar.followSet
        self.readTable()

    def updateParse(self, w):
        self.build_automata()
        self.buildTable()
        self.outputTable()
        self.parse(w)

if __name__ == "__main__":
    lexer = Lexer()
    lexer.configure('source.txt')

    g = Grammar()
    g.configure('MyGrammar.txt')

    print("Building automata...")
    t1 = time.time()
    p = Parser()
    p.configure(g)
    print("Analysis table completed in", '{:.4f}s'.format(time.time() - t1))

    print("Parsing...")
    t2 = time.time()
    # p.parse(lexer.output)
    p.updateParse(lexer.output)
    print("Syntactic analysis completed in", '{:.4f}s'.format(time.time() - t2))


