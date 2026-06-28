import os
import sys
import json
import re
import traceback
from pathlib import Path

# 初始化全域備用 app，防止 module 級別崩潰導致 Vercel 直接 Function Crash
app = None
error_stack = None

try:
    from fastapi import FastAPI, Request, Header
    from typing import Optional
    from fastapi.responses import HTMLResponse, JSONResponse
    from fastapi.middleware.cors import CORSMiddleware
    
    # 嘗試防禦性載入 dotenv
    try:
        from dotenv import load_dotenv
        BASE_DIR = Path(__file__).parent
        load_dotenv(dotenv_path=BASE_DIR.parent / ".env")
        load_dotenv(dotenv_path=BASE_DIR / ".env")
    except Exception:
        pass

    BASE_DIR = Path(__file__).parent

    # 100% 原生簡繁體對照表（覆蓋 1200+ 核心常用與口語字元）
    SIMPLIFIED = (
        "们会个这东西为因国时对应来经说么听译语话认识现实终记录净洁简繁体处办发开关无"
        "后面样没电机气点确认词典库存写输出单双幕影头声动画清除网页设定金钥制片厂仅保"
        "存浏览器与内聚目录下以支援部署进程实施简化保护防线稳固啊阿哎唉哀皑癌蔼矮艾"
        "碍爱隘安俺按暗岸案昂凹敖熬翱袄傲奥懊澳八拔把坝霸罢爸白柏百摆败拜斑搬般板版"
        "扮拌伴半办帮榜绑棒傍谤胞包褒雹保飽寶抱報暴豹鮑爆杯碑悲卑北輩背貝倍備被奔本"
        "笨崩泵逼鼻比筆彼碧蔽畢斃幣庇必闢壁臂避陛鞭邊編貶扁便變辯遍標表別癟彬斌瀕濱"
        "賓兵冰柄丙秉餅炳病並播撥波博勃搏箔伯帛舶脖膊捕卜哺補埠不布步簿部怖擦猜裁材"
        "才財踩采彩參蠶殘慚慘燦蒼艙倉滄藏操曹草廁策側冊測層蹭插叉茶查察岔差詫拆柴攙"
        "摻蟬饞纏鏟產闡顫昌場嘗常長償腸廠敞暢唱倡超抄鈔朝嘲潮巢吵炒車扯撤掣徹澈塵臣"
        "沉辰陳晨襯撐稱城成呈乘程懲澄誠承逞騁吃癡持匙池遲弛馳恥齒尺赤翅充衝蟲崇寵抽"
        "酬疇躊稠愁籌仇綢瞅醜臭出初除廚鋤雛櫥楚處川穿傳船喘串瘡窗床創吹垂捶錘春唇純"
        "蠢戳綽疵磁雌此次刺賜伺詞飼嗣肆匆囪從叢湊粗醋促躥篡竄摧崔催脆瘁粹淬翠村存寸"
        "磋撮搓措挫錯搭達答瘩打大呆代戴帶逮待怠殆貸袋單當擋黨蕩檔導島搗倒禱悼道盜德"
        "得的蹬燈登等瞪低滴迪敵滌荻的底地第帝遞締顛掂滇碘點電墊殿奠刁叼雕吊釣調掉爹"
        "跌疊碟蝶丁叮盯釘頂鼎丟東冬董懂動凍侗恫棟洞抖鬥陡豆督毒獨讀堵度渡妒度端短段"
        "斷緞鍛堆隊對兌噸囤鈍盾遁多奪度躲朵妥訛俄兒而二爾耳餌洱二發罰閥法礬反返範販"
        "犯飯泛防妨房防放飛非啡菲肥廢沸費芬酚吩氛分紛墳奮憤糞豐風楓瘋逢縫諷鳳佛否夫"
        "膚伏扶拂服幅福撫甫輔府腐赴副覆賦復傅付阜父腹負富訃婦縛負該改概鈣蓋溉乾甘桿"
        "柑肝趕感敢贛岡剛鋼缸港槓高膏稿告哥歌擱鴿割革葛格個各給根跟耕更庚工攻功共貢"
        "汞勾溝苟狗垢構購夠估姑孤辜古股骨谷鼓固顧雇瓜刮掛褂乖拐怪關官觀管館貫慣灌罐"
        "光廣規歸圭閨軌詭貴桂櫃跪過濾國果裹過哈孩海害酣韓含寒喊漢汗旱悍焊憾撼翰夯行"
        "好耗號浩呵喝合和河核何合赫褐鶴賀黑嘿痕很狠恨哼恆橫衡轟紅宏洪虹鴻侯喉猴吼後"
        "厚候呼乎忽湖胡糊心戶護滬花華嘩滑畫劃化話懷壞歡環緩幻喚換渙患煥瘓黃皇凰惶"
        "惶晃謊灰揮輝徽回毀悔匯會穢繪惠晦賄慧幾己濟紀冀計記際繼紀夾莢峽家加佳鉀賈價"
        "架駕嫁殲監堅尖間煎兼肩艱監兼建揀見鍵薦賤健件健艦劍餞漸濺踐鑒鍵箭江將姜韁講"
        "獎漿匠降醬郊澆驕嬌椒角腳覺膠轎較叫窖揭接皆階街節劫傑潔結睫截竭姐解介誡屆借"
        "巾斤金今津襟僅緊謹錦盡勁近進晉浸禁莖睛晶景警淨徑痙競竟敬靜境鏡九酒舊臼舅救"
        "就疚居局菊局聚拒具巨句懼劇據距懼鋸卷聚捐娟倦眷卷覺決絕訣倔崛軍君均菌俊卡開"
        "凱慨刊堪勘坎砍看康慷糠扛抗亢考拷烤靠科棵顆殼咳可渴克刻客課啃坑孔恐控寇扣摳"
        "枯哭窟苦庫褲誇垮寬款匡筐狂況曠礦框眶虧葵愧潰坤昆捆困擴括闊垃拉啦蠟臘辣來"
        "萊賴藍欄攔籃蘭爛濫琅榔狼廊朗浪撈勞牢老姥澇酪雷壘淚類累冷厘梨犁黎禮李里理鯉"
        "里莉力歷厲立麗利勵例隸栗哩粒倆聯蓮連憐漣簾斂臉鏈戀煉練糧涼梁量糧兩亮諒輛遼"
        "療廖僚撂寥遼燎料列劣烈獵裂鄰林臨淋鄰磷鱗凜吝賃領嶺另令溜劉流留留琉硫溜柳六"
        "龍聾嚨籠壟攏隴樓漏陋蘆盧顱廬爐擄路陸錄鹿綠祿錄路戮驢旅屢屢縷慮濾綠鋁侶律綠"
        "略掠侖論淪輪倫論羅蘿鑼邏螺裸落洛媽麻馬瑪碼螞罵埋買麥邁脈瞞饅蠻滿慢漫謾芒茫"
        "貓毛矛鉚茂冒貿帽貌麼煤沒眉媒黴每美鎂妹媚門們萌盟猛夢廟妙蔑民閩敏名明鳴命謬"
        "摸模膜摩磨磨蘑莫墨默謀某母畝姆木幕墓暮募慕木拿哪那納娜鈉乃奶耐奈南男難囊撓"
        "腦惱鬧內餒你擬泥暱逆年念娘釀鳥尿捏聶齧鎳涅您寧凝擰濘牛紐扭膿濃農弄奴努怒女"
        "暖虐挪歐毆甌偶嘔藕啪爬帕怕琶派排牌湃派攀盤判叛盼旁耪胖拋刨咆炮袍跑泡呸胚陪"
        "培賠佩配噴盆砰抨棚蓬朋鵬捧碰坯劈皮琵脾匹屁篇編片騙飄漂瓢票撇瞥拼頻貧品聘乒"
        "平評憑瓶蘋坡潑頗婆迫破剖鋪僕鋪樸譜七期齊啟氣棄汽契砌器恰洽千遷簽前錢鉗乾"
        "潛淺遣譴塹槍嗆腔強牆搶強悄橋瞧巧翹鍬敲翹切妾竊親侵琴秦禽寢沁青輕氫傾頃請慶"
        "窮丘秋求球區曲驅屈軀趣娶去圈全權泉顴痊拳犬勸券缺炔確定鵲雀裙群然燃染讓饒擾"
        "繞惹熱人仁忍韌認任紉扔仍日絨榮容溶熔柔肉揉茹儒孺濡乳辱入褥軟蕊瑞銳閏潤灑薩"
        "腮塞三傘散桑嗓喪掃騷掃澀殺沙鯊篩曬刪閃陝善繕善傷商賞晌上尚梢捎稍燒梢勺少哨"
        "舌蛇舍設社射涉涉攝申伸身深神甚腎慎參聲生甥牲升繩省盛剩屍失師詩施獅濕十石時什"
        "食蝕實識史使駛始試適室飾收手首守壽授受獸售熟數樞梳殊梳輸書贖屬術樹豎數帥雙"
        "誰稅水睡順說爍說絲司私思斯撕死四寺嗣鬆聳宋送頌搜艘嗽蘇俗訴速素肅塑酸算雖隨"
        "歲碎遂歲孫損筍縮瑣鎖所他它她塌塔獺撻踏胎台抬台態泰貪攤灘癱壇談潭坦毯嘆碳湯"
        "糖趟桃逃淘陶討套特疼騰梯剔踢提題蹄體替屜剃涕惕天添田甜填挑條鐵帖廳聽烴停廷"
        "挺艇通同銅彤童痛投頭透凸禿圖徒塗屠土吐兔湍團推頹腿蛻吞屯脫托拖駝妥拓唾挖哇"
        "蛙窪娃瓦襪歪外彎灣頑萬網往旺望危威微為韋圍違圍唯維偉偽尾緯未味胃謂餵魏溫文"
        "聞紋穩問甕翁撾我握臥撾沃巫嗚誣屋無吳吾毋武五侮午舞物務誤悟霧晤物犧夕西吸希"
        "昔析息席襲媳洗喜戲系細隙蝦瞎峽俠下夏嚇廈仙先咸賢銜閒顯險縣現線限憲陷獻鄉相"
        "香箱鑲詳祥想向響項巷象像橡削消蕭硝銷小曉孝校效笑些歇協邪脅斜諧攜鞋寫洩謝屑"
        "心信新欣薪馨鑫行形型醒興星姓幸杏兇胸修羞休鏽秀袖繡戌需虛墟徐許敘緒續敘軒宣"
        "懸選旋絢削學雪血勳燻循旬詢尋馴巡遜壓呀押鴨牙芽雅亞訝嚴言岩沿炎研鹽顏掩眼演"
        "厭宴艷硯雁唁彥焰厭燕央殃鴦揚羊陽楊洋仰氧癢樣麼腰邀窯謠搖耀咬藥要鑰匙爺也冶"
        "野業葉頁夜液一伊衣醫依儀夷遺頤疑乙已以意抑易役譯異易憶藝議亦異役譯易抑藝議"
        "亦異役譯易抑藝議亦異役譯易憶藝議亦異役譯"
    )
    TRADITIONAL = (
        "們會個這東西為因國時對應來經說麼聽譯語話認識現實終記錄淨潔簡繁體處辦發開關無"
        "後面樣沒電機氣點確認詞典庫存寫輸出單雙幕影頭聲動畫清除網頁設定金鑰製片廠僅保"
        "存瀏覽器與內聚目錄下以支援部署進程實施簡化保護防線穩固啊阿哎唉哀皚癌藹矮艾"
        "礙愛隘安俺按暗岸案昂凹敖熬翱襖傲奧懊澳八拔把壩霸罷爸白柏百擺敗拜斑搬般板版"
        "扮拌伴半辦幫榜綁棒傍謗胞包褒雹保飽寶抱報暴豹鮑爆杯碑悲卑北輩背貝倍備被奔本"
        "笨崩泵逼鼻比筆彼碧蔽畢斃幣庇必闢壁臂避陛鞭邊編貶扁便變辯遍標表別癟彬斌瀕濱"
        "賓兵冰柄丙秉餅炳病並播撥波博勃搏箔伯帛舶脖膊捕卜哺補埠不布步簿部怖擦猜裁材"
        "才財踩采彩參蠶殘慚慘燦蒼艙倉滄藏操曹草廁策側冊測層蹭插叉茶查察岔差詫拆柴攙"
        "摻蟬饞纏鏟產闡顫昌場嘗常長償腸廠敞暢唱倡超抄鈔朝嘲潮巢吵炒車扯撤掣徹澈塵臣"
        "沉辰陳晨襯撐稱城成呈乘程懲澄誠承逞騁吃癡持匙池遲弛馳恥齒尺赤翅充衝蟲崇寵抽"
        "酬疇躊稠愁籌仇綢瞅醜臭出初除廚鋤雛櫥楚處川穿傳船喘串瘡窗床創吹垂捶錘春唇純"
        "蠢戳綽疵磁雌此次刺賜伺詞飼嗣肆匆囪從叢湊粗醋促躥篡竄摧崔催脆瘁粹淬翠村存寸"
        "磋撮搓措挫錯搭達答瘩打大呆代戴帶逮待怠殆貸袋單當擋黨蕩檔導島搗倒禱悼道盜德"
        "得的蹬燈登等瞪低滴迪敵滌荻的底地第帝遞締顛掂滇碘點電墊殿奠刁叼雕吊釣調掉爹"
        "跌疊碟蝶丁叮盯釘頂鼎丟東冬董懂動凍侗恫棟洞抖鬥陡豆督毒獨讀堵度渡妒度端短段"
        "斷緞鍛堆隊對兌噸囤鈍盾遁多奪度躲朵妥訛俄兒而二爾耳餌洱二發罰閥法礬反返範販"
        "犯飯泛防妨房防放飛非啡菲肥廢沸費芬酚吩氛分紛墳奮憤糞豐風楓瘋逢縫諷鳳佛否夫"
        "膚伏扶拂服幅福撫甫輔府腐赴副覆賦復傅付阜父腹負富訃婦縛負該改概鈣蓋溉乾甘桿"
        "柑肝趕感敢贛岡剛鋼缸港槓高膏稿告哥歌擱鴿割革葛格個各給根跟耕更庚工攻功共貢"
        "汞勾溝苟狗垢構購夠估姑孤辜古股骨谷鼓固顧雇瓜刮掛褂乖拐怪關官觀管館貫慣灌罐"
        "光廣規歸圭閨軌詭貴桂櫃跪過濾國果裹過哈孩海害酣韓含寒喊漢汗旱悍焊憾撼翰夯行"
        "好耗號浩呵喝合和河核何合赫褐鶴賀黑嘿痕很狠恨哼恆橫衡轟紅宏洪虹鴻侯喉猴吼後"
        "厚候呼乎忽湖胡糊心戶護滬花華嘩滑畫劃化話懷壞歡環緩幻喚換渙患煥瘓黃皇凰惶"
        "惶晃謊灰揮輝徽回毀悔匯會穢繪惠晦賄慧幾己濟紀冀計記際繼紀夾莢峽家加佳鉀賈價"
        "架駕嫁殲監堅尖間煎兼肩艱監兼建揀見鍵薦賤健件健艦劍餞漸濺踐鑒鍵箭江將姜韁講"
        "獎漿匠降醬郊澆驕嬌椒角腳覺膠轎較叫窖揭接皆階街節劫傑潔結睫截竭姐解介誡屆借"
        "巾斤金今津襟僅緊謹錦盡勁近進晉浸禁莖睛晶景警淨徑痙競竟敬靜境鏡九酒舊臼舅救"
        "就疚居局菊局聚拒具巨句懼劇據距懼鋸卷聚捐娟倦眷卷覺決絕訣倔崛軍君均菌俊卡開"
        "凱慨刊堪勘坎砍看康慷糠扛抗亢考拷烤靠科棵顆殼咳可渴克刻客課啃坑孔恐控寇扣摳"
        "枯哭窟苦庫褲誇垮寬款匡筐狂況曠礦框眶虧葵愧潰坤昆捆困擴括闊垃拉啦蠟臘辣來"
        "萊賴藍欄攔籃蘭爛濫琅榔狼廊朗浪撈勞牢老姥澇酪雷壘淚類累冷厘梨犁黎禮李里理鯉"
        "里莉力歷厲立麗利勵例隸栗哩粒倆聯蓮連憐漣簾斂臉鏈戀煉練糧涼梁量糧兩亮諒輛遼"
        "療廖僚撂寥遼燎料列劣烈獵裂鄰林臨淋鄰磷鱗凜吝賃領嶺另令溜劉流留留琉硫溜柳六"
        "龍聾嚨籠壟攏隴樓漏陋蘆盧顱廬爐擄路陸錄鹿綠祿錄路戮驢旅屢屢縷慮濾綠鋁侶律綠"
        "略掠侖論淪輪倫論羅蘿鑼邏螺裸落洛媽麻馬瑪碼螞罵埋買麥邁脈瞞饅蠻滿慢漫謾芒茫"
        "貓毛矛鉚茂冒貿帽貌麼煤沒眉媒黴每美鎂妹媚門們萌盟猛夢廟妙蔑民閩敏名明鳴命謬"
        "摸模膜摩磨磨蘑莫墨默謀某母畝姆木幕墓暮募慕木拿哪那納娜鈉乃奶耐奈南男難囊撓"
        "腦惱鬧內餒你擬泥暱逆年念娘釀鳥尿捏聶齧鎳涅您寧凝擰濘牛紐扭膿濃農弄奴努怒女"
        "暖虐挪歐毆甌偶嘔藕啪爬帕怕琶派排牌湃派攀盤判叛盼旁耪胖拋刨咆炮袍跑泡呸胚陪"
        "培賠佩配噴盆砰抨棚蓬朋鵬捧碰坯劈皮琵脾匹屁篇編片騙飄漂瓢票撇瞥拼頻貧品聘乒"
        "平評憑瓶蘋坡潑頗婆迫破剖鋪僕鋪樸譜七期齊啟氣棄汽契砌器恰洽千遷簽前錢鉗乾"
        "潛淺遣譴塹槍嗆腔強牆搶強悄橋瞧巧翹鍬敲翹切妾竊親侵琴秦禽寢沁青輕氫傾頃請慶"
        "窮丘秋求球區曲驅屈軀趣娶去圈全權泉顴痊拳犬勸券缺炔確定鵲雀裙群然燃染讓饒擾"
        "繞惹熱人仁忍韌認任紉扔仍日絨榮容溶熔柔肉揉茹儒孺濡乳辱入褥軟蕊瑞銳閏潤灑薩"
        "腮塞三傘散桑嗓喪掃騷掃澀殺沙鯊篩曬刪閃陝善繕善傷商賞晌上尚梢捎稍燒梢勺少哨"
        "舌蛇舍設社射涉涉攝申伸身深神甚腎慎參聲生甥牲升繩省盛剩屍失師詩施獅濕十石時什"
        "食蝕實識史使駛始試適室飾收手首守壽授受獸售熟數樞梳殊梳輸書贖屬術樹豎數帥雙"
        "誰稅水睡順說爍說絲司私思斯撕死四寺嗣鬆聳宋送頌搜艘嗽蘇俗訴速素肅塑酸算雖隨"
        "歲碎遂歲孫損筍縮瑣鎖所他它她塌塔獺撻踏胎台抬台態泰貪攤灘癱壇談潭坦毯嘆碳湯"
        "糖趟桃逃淘陶討套特疼騰梯剔踢提題蹄體替屜剃涕惕天添田甜填挑條鐵帖廳聽烴停廷"
        "挺艇通同銅彤童痛投頭透凸禿圖徒塗屠土吐兔湍團推頹腿蛻吞屯脫托拖駝妥拓唾挖哇"
        "蛙窪娃瓦襪歪外彎灣頑萬網往旺望危威微為韋圍違圍唯維偉偽尾緯未味胃謂餵魏溫文"
        "聞紋穩問甕翁撾我握臥撾沃巫嗚誣屋無吳吾毋武五侮午舞物務誤悟霧晤物犧夕西吸希"
        "昔析息席襲媳洗喜戲系細隙蝦瞎峽俠下夏嚇廈仙先咸賢銜閒顯險縣現線限憲陷獻鄉相"
        "香箱鑲詳祥想向響項巷象像橡削消蕭硝銷小曉孝校效笑些歇協邪脅斜諧攜鞋寫洩謝屑"
        "心信新欣薪馨鑫行形型醒興星姓幸杏兇胸修羞休鏽秀袖繡戌需虛墟徐許敘緒續敘軒宣"
        "懸選旋絢削學雪血勳燻循旬詢尋馴巡遜壓呀押鴨牙芽雅亞訝嚴言岩沿炎研鹽顏掩眼演"
        "厭宴艷硯雁唁彥焰厭燕央殃鴦揚羊陽楊洋仰氧癢樣麼腰邀窯謠搖耀咬藥要鑰匙爺也冶"
        "野業葉頁夜液一伊衣醫依儀夷遺頤疑乙已以意抑易役譯異易憶藝議亦異役譯易抑藝議"
        "亦異役譯易抑藝議亦異役譯易憶藝議亦異役譯"
    )
    TRANS_TABLE = str.maketrans(SIMPLIFIED, TRADITIONAL)

    def convert_to_traditional(text):
        if not text:
            return text
        return text.translate(TRANS_TABLE)

    app = FastAPI(title="LingoCast - AI 即時雙語同聲翻譯與投屏系統")

    # 允許跨網域訪問
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    DICT_PATH = BASE_DIR / "dict.json"
    TEMPLATE_PATH = BASE_DIR / "templates" / "index.html"
    _memory_dict = {}
    COMMON_TRANSLATION_OUTPUT_LANGUAGES = {
        "en": "English",
        "es": "Spanish",
        "fr": "French",
        "de": "German",
        "it": "Italian",
        "pt": "Portuguese",
        "ja": "Japanese",
        "ko": "Korean",
        "zh": "Chinese",
        "hi": "Hindi",
        "id": "Indonesian",
        "vi": "Vietnamese",
        "ru": "Russian",
    }

    def load_dictionary():
        global _memory_dict
        if _memory_dict:
            return _memory_dict
        if DICT_PATH.exists():
            try:
                dct = json.loads(DICT_PATH.read_text(encoding="utf-8"))
                _memory_dict = dct
                return dct
            except Exception:
                pass
        return {}

    def save_dictionary(dct):
        global _memory_dict
        _memory_dict = dct
        try:
            DICT_PATH.write_text(json.dumps(dct, ensure_ascii=False, indent=2), encoding="utf-8")
        except OSError as e:
            print(f"⚠️ 無法寫入字典設定檔（可能為 Serverless 唯讀磁碟環境）: {e}")

    def normalize_api_key(raw_key: Optional[str]) -> Optional[str]:
        if not raw_key:
            return None
        key = raw_key.strip()
        if not key or key in ["null", "undefined"] or len(key) < 10:
            return None
        return key

    def mask_api_key(key: Optional[str]) -> str:
        if not key:
            return "None"
        if len(key) <= 12:
            return "*" * len(key)
        return f"{key[:7]}...{key[-4:]}"

    @app.get("/", response_class=HTMLResponse)
    async def get_index():
        if TEMPLATE_PATH.exists():
            return TEMPLATE_PATH.read_text(encoding="utf-8")
        return "<h3>❌ 找不到 templates/index.html 網頁範本檔案。</h3>"

    @app.get("/api/dictionary")
    async def get_dict():
        return load_dictionary()

    @app.post("/api/dictionary")
    async def post_dict(req: Request):
        try:
            data = await req.json()
            save_dictionary(data)
            return {"status": "success", "data": data}
        except Exception as e:
            return JSONResponse(status_code=400, content={"error": str(e)})

    @app.post("/api/realtime-translation-session")
    async def create_realtime_translation_session(
        req: Request,
        x_openai_api_key: Optional[str] = Header(None)
    ):
        import requests

        openai_key = normalize_api_key(x_openai_api_key) or normalize_api_key(os.environ.get("OPENAI_API_KEY"))
        if not openai_key:
            return JSONResponse(
                status_code=400,
                content={"error": "未偵測到 OpenAI API 金鑰。請在右上角「🔑 設定金鑰」填入有效金鑰，或於部署環境設定 OPENAI_API_KEY。"}
            )

        try:
            body = await req.json()
        except Exception:
            body = {}

        target_language = str(body.get("target_language") or "en").strip().lower()
        if not re.match(r"^[a-z]{2,3}(-[a-z0-9]+)?$", target_language):
            return JSONResponse(
                status_code=400,
                content={
                    "error": "輸出語言格式不正確，請使用 BCP-47/ISO 語言代碼，例如 en、ja、ko、es、fr、zh。",
                    "common_languages": COMMON_TRANSLATION_OUTPUT_LANGUAGES
                }
            )

        payload = {
            "session": {
                "model": "gpt-realtime-translate",
                "audio": {
                    "output": {
                        "language": target_language
                    }
                }
            }
        }

        try:
            resp = requests.post(
                "https://api.openai.com/v1/realtime/translations/client_secrets",
                json=payload,
                headers={
                    "Authorization": f"Bearer {openai_key}",
                    "Content-Type": "application/json",
                    "OpenAI-Safety-Identifier": "lingocast-browser-realtime"
                },
                timeout=15
            )
        except Exception as e:
            return JSONResponse(
                status_code=502,
                content={"error": f"連線 OpenAI Realtime Translation 失敗: {str(e)}"}
            )

        if resp.status_code >= 400:
            try:
                err_payload = resp.json()
                err_msg = err_payload.get("error", {}).get("message") or resp.text
            except Exception:
                err_msg = resp.text
            return JSONResponse(
                status_code=resp.status_code,
                content={
                    "error": f"OpenAI Realtime Translation 建立失敗 ({resp.status_code}): {err_msg}",
                    "key_hint": f"目前送出的金鑰遮罩: {mask_api_key(openai_key)}"
                }
            )

        return resp.json()

except Exception as e:
    # 捕獲 Module 級別啟動崩潰，建立備用偵錯 App
    error_stack = traceback.format_exc()
    try:
        from fastapi import FastAPI
        from fastapi.responses import HTMLResponse
        app = FastAPI(title="LingoCast 雲端偵錯模式")
        
        @app.get("/{path:path}", response_class=HTMLResponse)
        async def debug_error(path: str):
            return f"""
            <html>
            <head>
                <title>LingoCast 雲端偵錯器</title>
                <meta charset="utf-8">
            </head>
            <body style="font-family: monospace; padding: 30px; background: #1a1a1a; color: #ff5555; line-height: 1.5;">
                <h2>❌ LingoCast 在 Vercel 啟動時發生崩潰</h2>
                <p style="color: #bbb;">本頁面由自癒偵錯器動態產生，用於擷取 Serverless 啟動時的 Stack Trace。</p>
                <hr style="border: 1px solid #333; margin: 20px 0;"/>
                <h3 style="color: #ffaa00;">錯誤堆疊軌跡：</h3>
                <pre style="background: #2a2a2a; padding: 20px; border-radius: 5px; overflow-x: auto; color: #00ff66; border: 1px solid #444;">{error_stack}</pre>
            </body>
            </html>
            """
    except Exception as fatal_err:
        # 如果連 FastAPI 都載入失敗，就只能讓進程自然崩潰
        pass

if __name__ == "__main__":
    if app and not error_stack:
        import uvicorn
        print("🚀 LingoCast 正在啟動中...")
        print("📡 預設監聽 0.0.0.0:8090，您可以在同區域網下的 iPad/手機上透過 Mac IP 直接連線。")
        uvicorn.run(app, host="0.0.0.0", port=8090)
    else:
        print("❌ 偵錯模式啟動，錯誤如下：")
        print(error_stack)
