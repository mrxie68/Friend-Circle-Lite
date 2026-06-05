(function () {
  const config = window.PAGE_CONFIG || {};
  const friendsConfig = config.friends || {}; 
  const messageConfig = config.message || {};

  const baseUrl = friendsConfig.jsonUrl || "https://rss.minsp.org/";
  const safeBaseUrl = baseUrl.endsWith('/') ? baseUrl : baseUrl + '/';

  const excludedUsers = new Set(messageConfig.excludedUsers || []);

  const UserConfig = {
    private_api_url: safeBaseUrl,
    page_turning_number: friendsConfig.limit || 18,
    error_img: friendsConfig.errorImg || "https://img.minsp.org/images/2024/09/29/66f952f0c2520.webp",
    cache_duration: 10 * 60 * 1000, 
  };

  const createElement = (tag, className, text = '') => {
    const el = document.createElement(tag);
    if (className) el.className = className;
    if (text) el.textContent = text;
    return el;
  };

  const renderArticles = (articles, container) => {
    if (!articles.length) return;

    const fragment = document.createDocumentFragment();

    articles.forEach(article => {
      const link = createElement('a', 'fc-article-inline');
      link.href = article.link || '#';
      link.target = '_blank';
      link.rel = 'noopener noreferrer';

      const img = createElement('img', 'fc-article-avatar no-lightbox author-click');
      img.src = article.avatar || UserConfig.error_img;
      img.loading = "lazy";
      img.onerror = () => { img.src = UserConfig.error_img; };

      const author = createElement('div', 'fc-article-author author-click', article.author || '匿名');
      const title = createElement('div', 'fc-article-title', article.title || '无标题');
      
      const dateStr = article.created ? article.created.substring(0, 10) : '';
      const date = createElement('div', 'fc-article-date', dateStr);

      link.append(img, author, title, date);
      fragment.appendChild(link);
    });

    container.appendChild(fragment);
  };

  const safeSetLocalStorage = (key, value) => {
    try {
      localStorage.setItem(key, value);
    } catch (e) {
      console.warn('LocalStorage 设置失败', e);
    }
  };

  const safeGetLocalStorage = (key) => {
    try {
      return localStorage.getItem(key);
    } catch (e) {
      return null;
    }
  };

  const initFriendCircle = async () => {
    const root = document.getElementById('friend-circle-lite-root');
    const loader = document.getElementById('fc-loader');

    if (!root) return;

    if (root.hasAttribute('data-initialized')) return;
    root.setAttribute('data-initialized', 'true');

    let container = document.getElementById('fc-articles-container');
    if (!container) {
        container = document.createElement('div');
        container.className = 'fc-articles-container';
        container.id = 'fc-articles-container';
        if (loader) {
            root.insertBefore(container, loader);
        } else {
            root.appendChild(container);
        }
    } else {
        container.innerHTML = '';
    }

    const showLoader = (show) => {
      if (loader) loader.style.display = show ? 'block' : 'none';
    };

    try {
      showLoader(true);

      const cacheKey = 'friend-circle-lite-cache';
      const cacheTimeKey = 'friend-circle-lite-cache-time';
      const cacheTime = parseInt(safeGetLocalStorage(cacheTimeKey) || '0', 10);
      const now = Date.now();
      
      let data;

      if (now - cacheTime < UserConfig.cache_duration) {
        const cachedData = safeGetLocalStorage(cacheKey);
        if (cachedData) {
          try {
            data = JSON.parse(cachedData);
          } catch (e) {
            console.warn('朋友圈缓存解析失败');
          }
        }
      }

      if (!data) {
        const res = await fetch(`${UserConfig.private_api_url}all.json`);
        if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
        data = await res.json();
        
        safeSetLocalStorage(cacheKey, JSON.stringify(data));
        safeSetLocalStorage(cacheTimeKey, now.toString());
      }

      const fiveMonthsAgoTime = new Date();
      fiveMonthsAgoTime.setMonth(fiveMonthsAgoTime.getMonth() - 5);
      const timestampCutoff = fiveMonthsAgoTime.getTime();

      const validArticles = (data.article_data || []).filter(article => {
          if (excludedUsers.has(article.author)) return false;
          if (!article.created) return false;

          const safeDateStr = article.created.replace(/-/g, '/');
          const createdTime = new Date(safeDateStr).getTime();
          
          if (isNaN(createdTime)) return false; 
          return createdTime >= timestampCutoff;
      });

      let currentIndex = UserConfig.page_turning_number;
      
      // 渲染第一页
      renderArticles(validArticles.slice(0, currentIndex), container);

      // 🌟 核心修改：完全基于配置数值判断。配置大于20才启用分页加载按钮功能，与数据长度无关
      if (UserConfig.page_turning_number > 20) {
          let loadMoreBtn = document.getElementById('fc-load-more-btn');
          
          if (!loadMoreBtn) {
              loadMoreBtn = document.createElement('button');
              loadMoreBtn.id = 'fc-load-more-btn';
              loadMoreBtn.className = 'fc-load-more-btn';
              loadMoreBtn.style.cssText = 'display: block; margin: 20px auto; padding: 10px 20px; border: none; border-radius: 6px; background-color: var(--theme-color, #efefef); cursor: pointer; transition: 0.3s; color: var(--text-color, #333); font-size: 14px;';
              root.appendChild(loadMoreBtn);
          }

          const updateButtonState = () => {
              // 补充防御逻辑：即使配置了>20，如果数据已经被完全加载完毕，也必须隐藏按钮
              if (currentIndex >= validArticles.length) {
                  loadMoreBtn.style.display = 'none';
              } else {
                  loadMoreBtn.style.display = 'block';
                  loadMoreBtn.textContent = '加载更多';
              }
          };

          updateButtonState();

          loadMoreBtn.onclick = () => {
              const nextArticles = validArticles.slice(currentIndex, currentIndex + UserConfig.page_turning_number);
              renderArticles(nextArticles, container);
              currentIndex += UserConfig.page_turning_number;
              updateButtonState();
          };
      } else {
          // 配置数值在 1-20 之间，绝对不显示加载按钮
          const existingBtn = document.getElementById('fc-load-more-btn');
          if (existingBtn) existingBtn.style.display = 'none';
      }

    } catch (error) {
      console.error('朋友圈加载失败:', error);
      if (container) container.innerHTML = '<div class="text-center p-4">加载失败，请刷新重试。</div>';
    } finally {
      showLoader(false);
    }
  };

  if (!window._fc_astro_listener_added) {
    document.addEventListener('astro:page-load', initFriendCircle);
    window._fc_astro_listener_added = true;
  }

})();
