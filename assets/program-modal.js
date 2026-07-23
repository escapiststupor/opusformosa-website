(function () {
  var lang = (document.documentElement.getAttribute('lang') || '').toLowerCase().indexOf('en') === 0 ? 'en' : 'zh';

  var LABELS = {
    zh: { intermission: '中場休息', close: '關閉節目視窗', ariaTitle: '節目資訊' },
    en: { intermission: 'Intermission', close: 'Close program', ariaTitle: 'Program details' }
  };

  var PROGRAMS = {
    sep4: {
      zh: {
        date: '2026 · 9 月 4 日（週五）· 19:30',
        venue: '國家音樂廳，台北',
        title: 'Opus 開幕之夜：林易與朋友們',
        pieces: [
          { composer: '葛拉斯', composerAlt: 'Philip Glass',
            title: '〈開場〉，選自《玻璃工程》', titleAlt: 'Opening from Glassworks',
            performers: [{ role: '鋼琴', name: '林易' }] },
          { composer: '拉威爾', composerAlt: 'Maurice Ravel',
            title: '《圓舞曲》（雙鋼琴）', titleAlt: 'La Valse (two pianos)',
            performers: [
              { role: '鋼琴', name: '林易' },
              { role: '鋼琴', name: '小林愛実' }
            ] },
          { composer: '舒曼', composerAlt: 'Robert Schumann',
            title: '降 E 大調鋼琴四重奏，作品 47', titleAlt: 'Piano Quartet in E-flat major, Op. 47',
            performers: [
              { role: '小提琴', name: '黃凱珉' },
              { role: '中提琴', name: 'Adrien La Marca' },
              { role: '大提琴', name: '林恩俊' },
              { role: '鋼琴', name: '林易' }
            ] },
          { intermission: true },
          { composer: '蓋希文', composerAlt: 'George Gershwin',
            title: '《歌謠集》與前奏曲選段', titleAlt: 'Song-Book Selections & Preludes',
            performers: [{ role: '鋼琴', name: '林易' }] },
          { composer: '蕭士塔高維契', composerAlt: 'Dmitri Shostakovich',
            title: 'c 小調第一號鋼琴協奏曲，作品 35', titleAlt: 'Piano Concerto No. 1 in C minor, Op. 35',
            performers: [
              { role: '鋼琴', name: '林易' },
              { role: '指揮', name: '鄒佳宏' },
              { role: '樂團', name: '藝響室內樂團' }
            ] }
        ]
      },
      en: {
        date: 'Fri · Sep 4, 2026 · 19:30',
        venue: 'National Concert Hall, Taipei',
        title: 'Opus Music Festival — Opening Night: Steven Lin & Friends',
        pieces: [
          { composer: 'Philip Glass', composerAlt: '葛拉斯',
            title: '"Opening" from Glassworks', titleAlt: '〈開場〉，選自《玻璃工程》',
            performers: [{ role: 'Piano', name: 'Steven Lin' }] },
          { composer: 'Maurice Ravel', composerAlt: '拉威爾',
            title: 'La Valse (two pianos)', titleAlt: '《圓舞曲》（雙鋼琴）',
            performers: [
              { role: 'Piano', name: 'Steven Lin' },
              { role: 'Piano', name: 'Aimi Kobayashi' }
            ] },
          { composer: 'Robert Schumann', composerAlt: '舒曼',
            title: 'Piano Quartet in E-flat major, Op. 47', titleAlt: '降 E 大調鋼琴四重奏，作品 47',
            performers: [
              { role: 'Violin', name: 'Sirena Huang' },
              { role: 'Viola', name: 'Adrien La Marca' },
              { role: 'Cello', name: 'Eugene Lin' },
              { role: 'Piano', name: 'Steven Lin' }
            ] },
          { intermission: true },
          { composer: 'George Gershwin', composerAlt: '蓋希文',
            title: 'Song-Book Selections & Preludes', titleAlt: '《歌謠集》與前奏曲選段',
            performers: [{ role: 'Piano', name: 'Steven Lin' }] },
          { composer: 'Dmitri Shostakovich', composerAlt: '蕭士塔高維契',
            title: 'Piano Concerto No. 1 in C minor, Op. 35', titleAlt: 'c 小調第一號鋼琴協奏曲，作品 35',
            performers: [
              { role: 'Piano', name: 'Steven Lin' },
              { role: 'Conductor', name: 'Jia-Hung Zou' },
              { role: 'Orchestra', name: 'Opus Chamber Orchestra' }
            ] }
        ]
      }
    },

    sep9: {
      zh: {
        date: '2026 · 9 月 9 日（週三）· 19:30',
        venue: '衛武營國家藝術文化中心音樂廳，高雄',
        title: 'Opus 跨世代的樂聲：三重奏到協奏曲',
        pieces: [
          { composer: '康果爾德', composerAlt: 'Erich Wolfgang Korngold',
            title: '《無事生非》', titleAlt: 'Much Ado About Nothing',
            performers: [
              { role: '小提琴', name: '黃凱珉' },
              { role: '鋼琴', name: '林易' }
            ] },
          { composer: '拉赫瑪尼諾夫', composerAlt: 'Sergei Rachmaninoff',
            title: 'g 小調第一號《輓歌三重奏》', titleAlt: 'Trio élégiaque No. 1 in G minor',
            performers: [
              { role: '小提琴', name: 'Jinjoo Cho' },
              { role: '大提琴', name: 'Edgar Moreau' },
              { role: '鋼琴', name: '林易' }
            ] },
          { intermission: true },
          { composer: '海頓', composerAlt: 'Joseph Haydn',
            title: 'C 大調第一號大提琴協奏曲', titleAlt: 'Cello Concerto No. 1 in C major',
            performers: [
              { role: '大提琴', name: 'Edgar Moreau' },
              { role: '指揮', name: '鄒佳宏' },
              { role: '樂團', name: '藝響室內樂團' }
            ] },
          { composer: '蕭士塔高維契', composerAlt: 'Dmitri Shostakovich',
            title: 'c 小調第一號鋼琴協奏曲，作品 35', titleAlt: 'Piano Concerto No. 1 in C minor, Op. 35',
            performers: [
              { role: '鋼琴', name: '林易' },
              { role: '指揮', name: '鄒佳宏' },
              { role: '樂團', name: '藝響室內樂團' }
            ] }
        ]
      },
      en: {
        date: 'Wed · Sep 9, 2026 · 19:30',
        venue: 'Weiwuying Concert Hall, Kaohsiung',
        title: 'Opus Music Festival — Music Across Generations: From Trio to Concerto',
        pieces: [
          { composer: 'Erich Wolfgang Korngold', composerAlt: '康果爾德',
            title: 'Much Ado About Nothing', titleAlt: '《無事生非》',
            performers: [
              { role: 'Violin', name: 'Sirena Huang' },
              { role: 'Piano', name: 'Steven Lin' }
            ] },
          { composer: 'Sergei Rachmaninoff', composerAlt: '拉赫瑪尼諾夫',
            title: 'Trio élégiaque No. 1 in G minor', titleAlt: 'g 小調第一號《輓歌三重奏》',
            performers: [
              { role: 'Violin', name: 'Jinjoo Cho' },
              { role: 'Cello', name: 'Edgar Moreau' },
              { role: 'Piano', name: 'Steven Lin' }
            ] },
          { intermission: true },
          { composer: 'Joseph Haydn', composerAlt: '海頓',
            title: 'Cello Concerto No. 1 in C major', titleAlt: 'C 大調第一號大提琴協奏曲',
            performers: [
              { role: 'Cello', name: 'Edgar Moreau' },
              { role: 'Conductor', name: 'Jia-Hung Zou' },
              { role: 'Orchestra', name: 'Opus Chamber Orchestra' }
            ] },
          { composer: 'Dmitri Shostakovich', composerAlt: '蕭士塔高維契',
            title: 'Piano Concerto No. 1 in C minor, Op. 35', titleAlt: 'c 小調第一號鋼琴協奏曲，作品 35',
            performers: [
              { role: 'Piano', name: 'Steven Lin' },
              { role: 'Conductor', name: 'Jia-Hung Zou' },
              { role: 'Orchestra', name: 'Opus Chamber Orchestra' }
            ] }
        ]
      }
    },

    sep10: {
      zh: {
        date: '2026 · 9 月 10 日（週四）· 19:30',
        venue: '國家演奏廳，台北',
        title: 'Opus 室內樂系列 I《歐陸夜曲》',
        pieces: [
          { composer: '多納尼', composerAlt: 'Ernő Dohnányi',
            title: 'C 大調弦樂三重奏小夜曲，作品 10', titleAlt: 'Serenade in C major for String Trio, Op. 10',
            performers: [
              { role: '小提琴', name: '丁章媛' },
              { role: '中提琴', name: 'Adrien La Marca' },
              { role: '大提琴', name: 'Brannon Cho' }
            ] },
          { composer: '拉威爾', composerAlt: 'Maurice Ravel',
            title: 'a 小調鋼琴三重奏', titleAlt: 'Piano Trio in A minor',
            performers: [
              { role: '小提琴', name: 'Jinjoo Cho' },
              { role: '大提琴', name: 'Brannon Cho' },
              { role: '鋼琴', name: 'Kyu Yeon Kim' }
            ] },
          { intermission: true },
          { composer: '德弗札克', composerAlt: 'Antonín Dvořák',
            title: 'A 大調鋼琴五重奏，作品 81', titleAlt: 'Piano Quintet in A major, Op. 81',
            performers: [
              { role: '小提琴', name: '丁章媛' },
              { role: '小提琴', name: 'Boris Borgolotto' },
              { role: '中提琴', name: 'Adrien La Marca' },
              { role: '大提琴', name: 'Edgar Moreau' },
              { role: '鋼琴', name: '林易' }
            ] }
        ]
      },
      en: {
        date: 'Thu · Sep 10, 2026 · 19:30',
        venue: 'National Recital Hall, Taipei',
        title: 'Opus Music Festival — European Nocturne',
        pieces: [
          { composer: 'Ernő Dohnányi', composerAlt: '多納尼',
            title: 'Serenade in C major for String Trio, Op. 10', titleAlt: 'C 大調弦樂三重奏小夜曲，作品 10',
            performers: [
              { role: 'Violin', name: 'Belle Ting' },
              { role: 'Viola', name: 'Adrien La Marca' },
              { role: 'Cello', name: 'Brannon Cho' }
            ] },
          { composer: 'Maurice Ravel', composerAlt: '拉威爾',
            title: 'Piano Trio in A minor', titleAlt: 'a 小調鋼琴三重奏',
            performers: [
              { role: 'Violin', name: 'Jinjoo Cho' },
              { role: 'Cello', name: 'Brannon Cho' },
              { role: 'Piano', name: 'Kyu Yeon Kim' }
            ] },
          { intermission: true },
          { composer: 'Antonín Dvořák', composerAlt: '德弗札克',
            title: 'Piano Quintet in A major, Op. 81', titleAlt: 'A 大調鋼琴五重奏，作品 81',
            performers: [
              { role: 'Violin', name: 'Belle Ting' },
              { role: 'Violin', name: 'Boris Borgolotto' },
              { role: 'Viola', name: 'Adrien La Marca' },
              { role: 'Cello', name: 'Edgar Moreau' },
              { role: 'Piano', name: 'Steven Lin' }
            ] }
        ]
      }
    },

    sep12: {
      zh: {
        date: '2026 · 9 月 12 日（週六）· 19:30',
        venue: '國家演奏廳，台北',
        title: 'Opus 室內樂系列 II《異鄉之憶》',
        pieces: [
          { composer: '馬勒', composerAlt: 'Gustav Mahler',
            title: 'a 小調鋼琴四重奏', titleAlt: 'Piano Quartet in A minor',
            performers: [
              { role: '小提琴', name: '黃凱珉' },
              { role: '中提琴', name: 'Adrien La Marca' },
              { role: '大提琴', name: '林恩俊' },
              { role: '鋼琴', name: 'Kyu Yeon Kim' }
            ] },
          { composer: '佛瑞', composerAlt: 'Gabriel Fauré',
            title: 'g 小調第一號鋼琴四重奏，作品 15', titleAlt: 'Piano Quartet No. 1 in G minor, Op. 15',
            performers: [
              { role: '小提琴', name: 'Boris Borgolotto' },
              { role: '中提琴', name: 'Adrien La Marca' },
              { role: '大提琴', name: 'Brannon Cho' },
              { role: '鋼琴', name: 'Kyu Yeon Kim' }
            ] },
          { intermission: true },
          { composer: '柴可夫斯基', composerAlt: 'Pyotr Ilyich Tchaikovsky',
            title: 'd 小調弦樂六重奏《佛羅倫斯的回憶》，作品 70', titleAlt: 'String Sextet "Souvenir de Florence" in D minor, Op. 70',
            performers: [
              { role: '小提琴', name: 'Jinjoo Cho' },
              { role: '小提琴', name: '黃凱珉' },
              { role: '中提琴', name: 'Adrien La Marca' },
              { role: '中提琴', name: '陳志達' },
              { role: '大提琴', name: 'Edgar Moreau' },
              { role: '大提琴', name: 'Brannon Cho' }
            ] }
        ]
      },
      en: {
        date: 'Sat · Sep 12, 2026 · 19:30',
        venue: 'National Recital Hall, Taipei',
        title: 'Opus Music Festival — Souvenirs of a Distant Shore',
        pieces: [
          { composer: 'Gustav Mahler', composerAlt: '馬勒',
            title: 'Piano Quartet in A minor', titleAlt: 'a 小調鋼琴四重奏',
            performers: [
              { role: 'Violin', name: 'Sirena Huang' },
              { role: 'Viola', name: 'Adrien La Marca' },
              { role: 'Cello', name: 'Eugene Lin' },
              { role: 'Piano', name: 'Kyu Yeon Kim' }
            ] },
          { composer: 'Gabriel Fauré', composerAlt: '佛瑞',
            title: 'Piano Quartet No. 1 in G minor, Op. 15', titleAlt: 'g 小調第一號鋼琴四重奏，作品 15',
            performers: [
              { role: 'Violin', name: 'Boris Borgolotto' },
              { role: 'Viola', name: 'Adrien La Marca' },
              { role: 'Cello', name: 'Brannon Cho' },
              { role: 'Piano', name: 'Kyu Yeon Kim' }
            ] },
          { intermission: true },
          { composer: 'Pyotr Ilyich Tchaikovsky', composerAlt: '柴可夫斯基',
            title: 'String Sextet "Souvenir de Florence" in D minor, Op. 70', titleAlt: 'd 小調弦樂六重奏《佛羅倫斯的回憶》，作品 70',
            performers: [
              { role: 'Violin', name: 'Jinjoo Cho' },
              { role: 'Violin', name: 'Sirena Huang' },
              { role: 'Viola', name: 'Adrien La Marca' },
              { role: 'Viola', name: 'Chih-Ta Chen' },
              { role: 'Cello', name: 'Edgar Moreau' },
              { role: 'Cello', name: 'Brannon Cho' }
            ] }
        ]
      }
    },

    sep14: {
      zh: {
        date: '2026 · 9 月 14 日（週一）· 19:30',
        venue: '台中國家歌劇院中劇院，台中',
        title: 'Opus 室內樂系列 III《弦間絮語》',
        pieces: [
          { composer: '莫札特', composerAlt: 'Wolfgang Amadeus Mozart',
            title: 'G 大調小提琴與中提琴二重奏，K. 423', titleAlt: 'Duo for Violin and Viola in G major, K. 423',
            performers: [
              { role: '小提琴', name: '丁章媛' },
              { role: '中提琴', name: '陳志達' }
            ] },
          { composer: '葛拉納多斯', composerAlt: 'Enrique Granados',
            title: 'g 小調鋼琴五重奏', titleAlt: 'Piano Quintet in G minor',
            performers: [
              { role: '小提琴', name: 'Boris Borgolotto' },
              { role: '小提琴', name: 'Sophie Wang' },
              { role: '中提琴', name: '陳志達' },
              { role: '大提琴', name: 'Edgar Moreau' },
              { role: '鋼琴', name: '林易' }
            ] },
          { intermission: true },
          { composer: '布拉姆斯', composerAlt: 'Johannes Brahms',
            title: '降 B 大調第一號弦樂六重奏，作品 18', titleAlt: 'String Sextet No. 1 in B-flat major, Op. 18',
            performers: [
              { role: '小提琴', name: '黃凱珉' },
              { role: '小提琴', name: 'Boris Borgolotto' },
              { role: '中提琴', name: '陳志達' },
              { role: '中提琴', name: '嚴子晴' },
              { role: '大提琴', name: 'Edgar Moreau' },
              { role: '大提琴', name: '林恩俊' }
            ] }
        ]
      },
      en: {
        date: 'Mon · Sep 14, 2026 · 19:30',
        venue: 'National Taichung Theater · Playhouse, Taichung',
        title: 'Opus Music Festival — Whispers Between Strings',
        pieces: [
          { composer: 'Wolfgang Amadeus Mozart', composerAlt: '莫札特',
            title: 'Duo for Violin and Viola in G major, K. 423', titleAlt: 'G 大調小提琴與中提琴二重奏，K. 423',
            performers: [
              { role: 'Violin', name: 'Belle Ting' },
              { role: 'Viola', name: 'Chih-Ta Chen' }
            ] },
          { composer: 'Enrique Granados', composerAlt: '葛拉納多斯',
            title: 'Piano Quintet in G minor', titleAlt: 'g 小調鋼琴五重奏',
            performers: [
              { role: 'Violin', name: 'Boris Borgolotto' },
              { role: 'Violin', name: 'Sophie Wang' },
              { role: 'Viola', name: 'Chih-Ta Chen' },
              { role: 'Cello', name: 'Edgar Moreau' },
              { role: 'Piano', name: 'Steven Lin' }
            ] },
          { intermission: true },
          { composer: 'Johannes Brahms', composerAlt: '布拉姆斯',
            title: 'String Sextet No. 1 in B-flat major, Op. 18', titleAlt: '降 B 大調第一號弦樂六重奏，作品 18',
            performers: [
              { role: 'Violin', name: 'Sirena Huang' },
              { role: 'Violin', name: 'Boris Borgolotto' },
              { role: 'Viola', name: 'Chih-Ta Chen' },
              { role: 'Viola', name: 'Canglah Micyang' },
              { role: 'Cello', name: 'Edgar Moreau' },
              { role: 'Cello', name: 'Eugene Lin' }
            ] }
        ]
      }
    },

    sep16: {
      zh: {
        date: '2026 · 9 月 16 日（週三）· 19:30',
        venue: '台中國家歌劇院大劇院，台中',
        title: 'Opus 閉幕之夜：林易與朋友們',
        pieces: [
          { composer: '康果爾德', composerAlt: 'Erich Wolfgang Korngold',
            title: '《無事生非》', titleAlt: 'Much Ado About Nothing',
            performers: [
              { role: '小提琴', name: '丁章媛' },
              { role: '鋼琴', name: '林易' }
            ] },
          { composer: '拉赫瑪尼諾夫', composerAlt: 'Sergei Rachmaninoff',
            title: 'g 小調第一號《輓歌三重奏》', titleAlt: 'Trio élégiaque No. 1 in G minor',
            performers: [
              { role: '小提琴', name: '丁章媛' },
              { role: '大提琴', name: 'Edgar Moreau' },
              { role: '鋼琴', name: '林易' }
            ] },
          { intermission: true },
          { composer: '海頓', composerAlt: 'Joseph Haydn',
            title: 'C 大調第一號大提琴協奏曲', titleAlt: 'Cello Concerto No. 1 in C major',
            performers: [
              { role: '大提琴', name: 'Edgar Moreau' },
              { role: '指揮', name: '鄒佳宏' },
              { role: '樂團', name: '藝響室內樂團' }
            ] },
          { composer: '蕭士塔高維契', composerAlt: 'Dmitri Shostakovich',
            title: 'c 小調第一號鋼琴、小號與弦樂團協奏曲，作品 35', titleAlt: 'Concerto No. 1 for Piano, Trumpet and Strings in C minor, Op. 35',
            performers: [
              { role: '鋼琴', name: '林易' },
              { role: '小號', name: '侯傅安' },
              { role: '指揮', name: '鄒佳宏' },
              { role: '樂團', name: '藝響室內樂團' }
            ] }
        ]
      },
      en: {
        date: 'Wed · Sep 16, 2026 · 19:30',
        venue: 'National Taichung Theater · Grand Theater, Taichung',
        title: 'Opus Music Festival — Closing Night: Steven Lin & Friends',
        pieces: [
          { composer: 'Erich Wolfgang Korngold', composerAlt: '康果爾德',
            title: 'Much Ado About Nothing', titleAlt: '《無事生非》',
            performers: [
              { role: 'Violin', name: 'Belle Ting' },
              { role: 'Piano', name: 'Steven Lin' }
            ] },
          { composer: 'Sergei Rachmaninoff', composerAlt: '拉赫瑪尼諾夫',
            title: 'Trio élégiaque No. 1 in G minor', titleAlt: 'g 小調第一號《輓歌三重奏》',
            performers: [
              { role: 'Violin', name: 'Belle Ting' },
              { role: 'Cello', name: 'Edgar Moreau' },
              { role: 'Piano', name: 'Steven Lin' }
            ] },
          { intermission: true },
          { composer: 'Joseph Haydn', composerAlt: '海頓',
            title: 'Cello Concerto No. 1 in C major', titleAlt: 'C 大調第一號大提琴協奏曲',
            performers: [
              { role: 'Cello', name: 'Edgar Moreau' },
              { role: 'Conductor', name: 'Jia-Hung Zou' },
              { role: 'Orchestra', name: 'Opus Chamber Orchestra' }
            ] },
          { composer: 'Dmitri Shostakovich', composerAlt: '蕭士塔高維契',
            title: 'Concerto No. 1 for Piano, Trumpet and Strings in C minor, Op. 35', titleAlt: 'c 小調第一號鋼琴、小號與弦樂團協奏曲，作品 35',
            performers: [
              { role: 'Piano', name: 'Steven Lin' },
              { role: 'Trumpet', name: 'Chuan-An Hou' },
              { role: 'Conductor', name: 'Jia-Hung Zou' },
              { role: 'Orchestra', name: 'Opus Chamber Orchestra' }
            ] }
        ]
      }
    }
  };

  function escapeHtml(s) {
    return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  function buildModal() {
    var el = document.createElement('div');
    el.id = 'program-modal';
    el.className = 'program-modal';
    el.setAttribute('role', 'dialog');
    el.setAttribute('aria-modal', 'true');
    el.setAttribute('aria-labelledby', 'program-modal-title');
    el.setAttribute('aria-label', LABELS[lang].ariaTitle);
    el.hidden = true;
    el.innerHTML =
      '<div class="program-modal-overlay" data-modal-close></div>' +
      '<div class="program-modal-panel" role="document">' +
      '<button type="button" class="program-modal-close" data-modal-close aria-label="' + escapeHtml(LABELS[lang].close) + '">' +
      '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path d="M18 6L6 18M6 6l12 12"/></svg>' +
      '</button>' +
      '<p class="program-modal-eyebrow" data-modal-date></p>' +
      '<h2 id="program-modal-title" class="program-modal-title" data-modal-title></h2>' +
      '<p class="program-modal-venue" data-modal-venue></p>' +
      '<div class="program-modal-pieces" data-modal-pieces></div>' +
      '</div>';
    document.body.appendChild(el);
    return el;
  }

  function renderPieces(pieces) {
    return pieces.map(function (p) {
      if (p.intermission) {
        return '<div class="program-intermission">' + escapeHtml(LABELS[lang].intermission) + '</div>';
      }
      var perfHtml = p.performers.map(function (person) {
        return '<div><span class="perf-role">' + escapeHtml(person.role) + '</span>' + escapeHtml(person.name) + '</div>';
      }).join('');
      var altHtml = p.titleAlt ? '<div class="program-piece-title-alt">' + escapeHtml(p.titleAlt) + '</div>' : '';
      var composerAlt = p.composerAlt ? ' <span style="color:rgba(200,152,64,0.55);font-weight:400;font-size:0.9rem;">· ' + escapeHtml(p.composerAlt) + '</span>' : '';
      return '<div class="program-piece">' +
        '<div class="program-piece-body">' +
        '<div class="program-piece-composer">' + escapeHtml(p.composer) + composerAlt + '</div>' +
        '<div class="program-piece-title">' + escapeHtml(p.title) + '</div>' +
        altHtml +
        '<div class="program-piece-performers">' + perfHtml + '</div>' +
        '</div>' +
        '</div>';
    }).join('');
  }

  var modalEl = null;
  var lastFocused = null;

  function ensureModal() {
    if (!modalEl) modalEl = buildModal();
    return modalEl;
  }

  function open(id) {
    var entry = PROGRAMS[id];
    if (!entry) return;
    var data = entry[lang];
    if (!data) return;
    var m = ensureModal();
    m.querySelector('[data-modal-date]').textContent = data.date;
    m.querySelector('[data-modal-title]').textContent = data.title;
    m.querySelector('[data-modal-venue]').textContent = data.venue;
    m.querySelector('[data-modal-pieces]').innerHTML = renderPieces(data.pieces);
    m.querySelector('.program-modal-panel').scrollTop = 0;
    lastFocused = document.activeElement;
    m.hidden = false;
    document.body.classList.add('program-modal-open');
    var closeBtn = m.querySelector('.program-modal-close');
    if (closeBtn) closeBtn.focus();
  }

  function close() {
    if (!modalEl || modalEl.hidden) return;
    modalEl.hidden = true;
    document.body.classList.remove('program-modal-open');
    if (lastFocused && typeof lastFocused.focus === 'function') {
      lastFocused.focus();
    }
  }

  document.addEventListener('click', function (e) {
    var trigger = e.target.closest('[data-program]');
    if (trigger) {
      e.preventDefault();
      open(trigger.getAttribute('data-program'));
      return;
    }
    var closer = e.target.closest('[data-modal-close]');
    if (closer && modalEl && modalEl.contains(closer)) {
      close();
    }
  });

  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && modalEl && !modalEl.hidden) {
      close();
    }
  });
})();
