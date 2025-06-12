export default async function initNavBar() {
  const titles = "h2, h3, h4";
  const nav = ".LeftNav a";
  const leftNav = document.querySelector(".LeftNav");
  const siteContent = document.querySelector(".og-Content");
  let isObserverDisabled = false;
  function el(type = "", props = {}, ...children) {
    if (!type) {
      throw new Error("Provide `type` to create document element.");
    }
    const docEl = Object.assign(document.createElement(type), props);
    children.forEach((child) => {
      if (typeof child === "string") {
        docEl.appendChild(document.createTextNode(child));
      } else if (Array.isArray(child)) {
        child.forEach((c) => docEl.appendChild(c));
      } else if (child instanceof HTMLElement) {
        docEl.appendChild(child);
      }
    });
    return docEl;
  }
  function buildNav() {
    return new Promise((resolve, reject) => {
      let navItems = [];
      let elements = [];
      if (!siteContent || !leftNav) {
        return reject(".og-Content not found.");
      }
      if (leftNav instanceof HTMLElement && !leftNav?.dataset?.hydrate) {
        return resolve(true);
      }
      for (const title of siteContent.querySelectorAll(titles)) {
        if (title instanceof HTMLElement && !title?.dataset?.ignore) {
          switch (title.tagName) {
            case "H2":
              navItems = [
                ...navItems,
                {
                  id: title.id,
                  label: title?.dataset?.title ? title.dataset.title : title.textContent ?? ""
                }
              ];
              break;
            case "H3":
            case "H4":
              if (!navItems[navItems.length - 1]?.subnav) {
                navItems[navItems.length - 1].subnav = [
                  {
                    id: title.id,
                    label: title?.dataset?.title ? title.dataset.title : title.textContent ?? ""
                  }
                ];
              } else if (navItems[navItems.length - 1].subnav) {
                navItems[navItems.length - 1].subnav?.push({
                  id: title.id,
                  label: title?.dataset?.title ? title.dataset.title : title.textContent ?? ""
                });
              }
              break;
          }
        }
      }
      for (const navItem of navItems) {
        const link = el("a", { href: "#" + navItem.id }, el("span", {}, navItem.label));
        elements = [...elements, link];
        if (navItem?.subnav) {
          let subLinks = [];
          for (const subnavItem of navItem.subnav) {
            const subItem = el(
              "li",
              {},
              el(
                "a",
                { href: "#" + subnavItem.id },
                el("img", { src: "/assets/dot.svg", width: "5", height: "5" }),
                el("span", {}, subnavItem.label)
              )
            );
            subLinks = [...subLinks, subItem];
          }
          const list = el("ul", { className: "LeftSubnav" }, subLinks);
          elements = [...elements, list];
        }
      }
      elements.forEach((element) => leftNav.appendChild(element));
      return resolve(true);
    });
  }
  function setNav() {
    return new Promise((resolve) => {
      const links = document.querySelectorAll(nav)
      if (!links.length) return resolve(true);
      for (const a of links) {
        if (a instanceof HTMLAnchorElement && a.href.split("#")[1] === location.hash.slice(1)) {
          setElementActive(a);
          break;
        }
      }
      resolve(true);
    });
  }
  function resetNav() {
    document.querySelectorAll(nav).forEach(a => a.classList.remove("active"));
  }
  function setElementActive(element) {
    if (!(element instanceof HTMLAnchorElement)) return;

    resetNav();
    element.classList.add("active");

    const parentList = element.closest(".LeftSubnav");
    if (parentList) {
      const topLink = parentList.previousElementSibling;
      if (topLink instanceof HTMLAnchorElement) {
        topLink.classList.add("active");
      }
    }
  }
  function setLinkManually() {
    delayObserver();
    const link = document.querySelector('[href="' + location.hash + '"]');
    if (link instanceof HTMLAnchorElement) {
      setElementActive(link);
    }
  }
  function delayObserver() {
    isObserverDisabled = true;
    setTimeout(() => {
      isObserverDisabled = false;
    }, 200);
  }
function observeSections() {
  let lastScrollY = window.scrollY;

  const callback = (entries) => {
    if (isObserverDisabled) return;

    const scrollDown = window.scrollY > lastScrollY;
    lastScrollY = window.scrollY;

    // Get all intersecting entries whose top is inside viewport
    const candidates = entries
      .filter(entry => entry.isIntersecting && entry.target instanceof HTMLElement)
      .map(entry => ({
        entry,
        top: entry.target.getBoundingClientRect().top
      }));

    if (candidates.length === 0) return;

    // Sort: if scrolling down, take the lowest heading in view
    // if scrolling up, take the highest heading in view
    candidates.sort((a, b) => scrollDown ? b.top - a.top : a.top - b.top);

    const { id } = candidates[0].entry.target;
    const link = document.querySelector(`.LeftNav a[href="#${id}"]`);
    if (link instanceof HTMLAnchorElement) {
      setElementActive(link);
    }
  };

  const observer = new IntersectionObserver(callback, {
    rootMargin: '0px 0px -60% 0px',
    threshold: 0.1
  });

  siteContent.querySelectorAll(titles).forEach(el => {
    if (el instanceof HTMLElement && !el.dataset.ignore) {
      observer.observe(el);
    }
  });

  window.addEventListener("hashchange", setLinkManually);
}

  try {
    await buildNav();
    await setNav();

    if (location.hash) {
      const link = document.querySelector(`.LeftNav a[href="${location.hash}"]`);
      if (link instanceof HTMLAnchorElement) {
        setElementActive(link);
        delayObserver(); // prevent flicker by delaying observer after jump
      }
    }

    observeSections();
  } catch (e) {
    if (e instanceof Error) {
      console.error(e.message);
    } else {
      console.error(e);
    }
  }
};
