# «Колобок» — 3D пиксель-арт (HD-2D), 60 с

Объёмные воксельные персонажи (пиксели в 3D) в настоящей 3D-диораме: точечный свет с тенями, туман, tilt-shift,
bloom, RPG-окна с пиксельным текстом (Press Start 2P, кириллица), комикс-представления
героев в стиле супергеройских комиксов при первом появлении. Сказка без изменений,
текст по обработке А. Н. Толстого. План, планы, музыка и звук описаны в `TREATMENT.md`.

Собирается в библиотеке [lemo-opuscar](https://github.com/danildanilzaichikov-blip/lemo-opuscar)
(стиль `hd-2d`, движок three.js, рендер Playwright):

```sh
# из корня lemo-opuscar: зависимости (npm + .venv)
sh plugin/skills/lemo-opuscar/scripts/setup.sh deps
mkdir -p films && cp -r <этот каталог> films/kolobok
node core/render/still.mjs films/kolobok 6 26.5 44 --q ss=1           # проверочные кадры
node core/render/video.mjs films/kolobok --fps 24 --workers 3 --q ss=1 --out films/kolobok/out/video.mp4
.venv/bin/python films/kolobok/mix.py                                  # музыка и звуки → out/mix.wav
sh core/render/mux.sh films/kolobok/out/video.mp4 films/kolobok/out/mix.wav films/kolobok/kolobok.mp4 24 0
```

`ss=2` даёт суперсэмплинг (чище края, в 4 раза медленнее; на машине без GPU кадр ≈ 2,7 с при ss=1).

- `timeline.json` — единый таймлайн: планы, встречи, текст, реплики, титулы; его читают и
  страница, и `mix.py`.
- `world.js` — диорама-дорога (изба, березняк, ельник, чаща, поляна) и свет по времени суток;
  `inside.js` — изба в разрезе с печью; `cast.js` — спрайты и путь колобка; `ui.js` —
  пиксельный текст, плавно проявляющийся по словам.
- `px.js`, `kit.js`, `fx.js`, `post_ts.js` — копии модулей стиля hd-2d из lemo-opuscar.
- `voxels.js` + `voxels.json` — персонажи из вокселей: те же 3D-примитивы, что у спрайтов,
  ступенчатые палитры запечены, свет и тени сцены поверх.
- `rigs.js` — шарнирные воксельные существа (звери с лапами из двух сегментов, головой и
  хвостом на шарнирах; люди; птицы, бабочки, белка, ёжик, сова, олень); `actors.js` —
  маршруты: выходы из леса и уходы, шаг по пройденному пути без скольжения.
- `sprites/` — деревья, подлесок, предметы и портреты для комикс-панелей, отрисованные объёмным пиксельным движком
  `sprite-engine/` (3D-примитивы → нормали → квантованные палитры).
