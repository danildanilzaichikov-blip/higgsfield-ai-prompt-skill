# «Колобок» — пересказ за 1 минуту

Классическая сказка без изменений сюжета, текст по обработке А. Н. Толстого. Восемь
локаций, персонажи появляются в кадре как фотореалистичные «вырезки», под ними
всплывает описание действий, реплики идут в пузырях. Переходы плавные, через растворение
с волшебной пылью. Музыка сказочная: арфа, музыкальная шкатулка, струнные.

**Вид — не 2D.** Персонажи и места выглядят «как на самом деле»: живые заяц, волк,
медведь и лиса, старик и старуха в настоящей крестьянской одежде XIX века, колобок как
настоящий хлеб. Картинки генерируются в Higgsfield (Шаг 1), ролик собирается скриптом
(Шаг 2).

## Сюжет и тайминг (0:00–1:00)

| Время | Локация | Кто появляется | Текст (всплывает) |
|---|---|---|---|
| 0:00–0:07 | Двор у избы | старик, старуха | Жили-были старик со старухой. Вот и просит старик: «Испеки мне колобок». |
| 0:07–0:15 | Изба, русская печь | старуха, колобок | По амбару помела, по сусекам поскребла… замесила на сметане, изжарила в масле… |
| 0:15–0:21 | Окошко | колобок | Положила его старуха на окошечко постудить. Колобок полежал-полежал, да и покатился! |
| 0:21–0:28 | Березняк | колобок, заяц | «Колобок, колобок! Я тебя съем!» — «Я от дедушки ушёл, я от бабушки ушёл…» |
| 0:28–0:34 | Ельник | колобок, волк | «…а от тебя, волк, не хитро уйти!» |
| 0:34–0:41 | Чаща | колобок, медведь | «…а от тебя, медведь, не хитро уйти!» |
| 0:41–0:53 | Поляна на закате | колобок, лиса | «Сядь ко мне на язычок да пропой ещё разок». Колобок прыг лисе на язык, а лиса его — ам! — и съела. |
| 0:53–1:00 | Ночь над избой | — | Тут и сказке конец, а кто слушал — молодец! |

## Шаг 1. Картинки в Higgsfield

**Персонажи:** GPT Image 2.0 или Nano Banana Pro, формат **3:4**, по одному на
картинку. Фон строго белый: скрипт вырезает персонажа сам, белое внутри фигуры (борода,
грудка лисы) не трогает. Сохраните как PNG в `render/chars/` под указанными именами.

Общий хвост для всех персонажей (вставлять в конец каждого промта):

```text
Photorealistic, natural anatomy and proportions, realistic fur / fabric / skin texture,
soft even studio daylight from the upper left, sharp focus, full figure visible from
head to feet, centered. Isolated on a plain pure white background, no ground, no cast
shadow on the background, no frame, no text, no watermark.
```

| Файл | Промт |
|---|---|
| `ded.png` | A Russian peasant man of the 19th century, the old man from the folk tale: long grey beard, kind weathered face, thin grey hair; long linen kosovorotka shirt embroidered in red at the collar and hem, worn outside the trousers and tied with a woven red sash; striped homespun trousers; birch-bark bast shoes (lapti) over white foot wrappings bound with cords. Standing calmly, hands folded in front. |
| `baba.png` | A Russian peasant woman of the 19th century, the old woman from the folk tale: kind face with soft wrinkles; dark red sarafan over a white linen shirt with full sleeves embroidered in red at the shoulders, plain linen apron, patterned woollen headscarf tied under the chin; bast shoes. Standing, holding a wooden bowl of dough in both hands. |
| `kolobok.png` | A round rustic Russian bread bun (kolobok), the size of a small melon, golden-brown glossy crust fried in butter, slightly uneven hand-shaped surface, light dusting of flour. Seen from the front, sitting on its own. |
| `hare.png` | A European brown hare in summer coat, grey-brown fur, long black-tipped ears upright, sitting up on its hind legs, alert, facing left. |
| `wolf.png` | A grey Eurasian wolf, thick grey and tawny fur, standing side-on, head lowered, looking left with a hungry stare. |
| `bear.png` | A Eurasian brown bear standing up on its hind legs, shaggy dark-brown fur, front paws raised, looking toward the left. |
| `fox.png` | A red fox sitting, bushy tail with a white tip wrapped around its front paws, sly half-closed amber eyes, head tilted, looking left. |

Звери смотрят влево, потому что колобок вкатывается в кадр слева. Если колобок нужен с
лицом, как в книжках, допишите в его промт: «with a simple friendly face pressed into
the dough: two raisin eyes and a smiling mouth».

**Локации:** та же модель, формат **16:9**, PNG в `render/bg/`. Хвост для всех:

```text
Photorealistic landscape photograph, natural light, deep focus, no people, no animals,
no text. The lower third is open ground where figures will stand.
```

| Файл | Промт |
|---|---|
| `village.png` | A Russian village homestead in summer: a log izba with carved white window frames and blue shutters, a wooden fence, sunflowers, a dirt path, fields and birch groves on distant hills, cumulus clouds. |
| `kitchen.png` | Inside a 19th-century Russian peasant izba: a big whitewashed Russian stove on the right with an arched mouth glowing with fire, log walls, a wooden table with a clay bowl and a sack of flour, an embroidered towel on the wall, light from a small window. |
| `window.png` | An izba window seen from inside: carved wooden window frame, a wide wooden windowsill empty in the lower centre, checked curtains, summer birch trees outside. |
| `birches.png` | A sunny birch grove with a forest path, chamomile flowers, soft green light. |
| `spruce.png` | A dense spruce forest, moss, red fly-agaric mushrooms, a narrow path, cool shadows. |
| `thicket.png` | A deep old forest thicket: massive oak trunks, raspberry bushes, a fallen log, a wild beehive on a branch, dim green light. |
| `glade.png` | A forest glade at golden sunset, tall grass, a tree stump on the right, warm low sun through birch trunks. |
| `night.png` | A village izba at night under a crescent moon and stars, one warm lit window, dark spruces around. |

Делайте 2–4 варианта и берите тот, где персонаж целиком в кадре и фон чисто белый.

## Шаг 2. Сборка ролика

```bash
cd docs/productions/kolobok/render
# шрифты (OFL, Google Fonts): Ruslan.ttf (Ruslan Display) и Philosopher-Bold.ttf
python3 audio.py track.wav            # музыка и звуки
python3 render.py video.mp4           # 1440 кадров, 1080p/24
ffmpeg -i video.mp4 -i track.wav -c:v copy -c:a aac -shortest kolobok.mp4
```

Если какой-то картинки нет, скрипт подставит рисованную заглушку, так что ролик
собирается в любой момент. Финальный вид получится, когда в `chars/` и `bg/` лежат все
15 картинок.

Что делает сборка:

- персонаж «поднимается» в кадр снизу вверх, слегка покачивается и уходит;
- колобок катится с поворотом, прыгает с окошка и на язык лисе;
- камера медленно наезжает или панорамирует внутри каждой локации;
- между локациями 1,1 с растворения с волшебной пылью;
- описание действий всплывает по словам на ленте сверху, реплики в пузырях;
- звук: арфа и музыкальная шкатулка в ре миноре, в сцене с лисой музыка становится
  тревожнее; треск печи, птицы в березняке, рык медведя, «ам», сова в финале.
