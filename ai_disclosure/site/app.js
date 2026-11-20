/* AI disclosure: draws the report of a project from data/<slug>.json.
   Plain browser JavaScript, no dependency. Every text coming from the data is
   inserted with textContent. */
(function () {
  "use strict";

  const SVG = "http://www.w3.org/2000/svg";
  const NONE = "No AI declared";
  const TOOL = "tool, model not named";
  const TOOL_NOTE = "Some trailers name a tool and not a model: GitHub Copilot, for instance, works with the models of several vendors and does not say which one. Such a commit declares the use of AI and is counted like the others, but the model behind it is not known. It is shown as “tool, model not named”, under the vendor of the tool.";
  const number = new Intl.NumberFormat("en");
  const compact = new Intl.NumberFormat("en", { notation: "compact", maximumFractionDigits: 1 });
  const root = document.getElementById("report");
  const tooltip = document.getElementById("tooltip");

  function el(tag, attributes, ...children) {
    const node = document.createElement(tag);
    for (const [key, value] of Object.entries(attributes || {})) {
      if (value === null || value === undefined || value === false) continue;
      if (key === "class") node.className = value;
      else if (key === "text") node.textContent = value;
      else if (key.startsWith("on")) node.addEventListener(key.slice(2), value);
      else node.setAttribute(key, value === true ? "" : value);
    }
    for (const child of children.flat()) {
      if (child === null || child === undefined || child === false) continue;
      node.append(child);
    }
    return node;
  }

  function svg(tag, attributes) {
    const node = document.createElementNS(SVG, tag);
    for (const [key, value] of Object.entries(attributes || {})) node.setAttribute(key, value);
    return node;
  }

  function percent(part, whole) {
    if (!whole) return "–";
    const value = (100 * part) / whole;
    return (value > 0 && value < 1 ? "<1" : String(Math.round(value))) + "%";
  }

  function day(iso) {
    if (!iso) return "";
    const [year, month, date] = iso.split("-").map(Number);
    return new Date(Date.UTC(year, month - 1, date || 1)).toLocaleDateString("en-GB", {
      day: date ? "numeric" : undefined, month: "short", year: "numeric", timeZone: "UTC",
    });
  }

  function monthName(key) {
    const [year, month] = key.split("-").map(Number);
    return new Date(Date.UTC(year, month - 1, 1)).toLocaleDateString("en-GB", {
      month: "long", year: "numeric", timeZone: "UTC",
    });
  }

  function plural(count, one, many) {
    return number.format(count) + " " + (count === 1 ? one : many || one + "s");
  }

  // Colours follow the model families, in the order of the report, in every chart.
  function colours(report) {
    const map = new Map();
    report.families.forEach((family, index) => map.set(family.id, `var(--series-${Math.min(index, 7) + 1})`));
    map.set(NONE, "var(--none)");
    return map;
  }

  function swatch(colour) {
    return el("span", { class: "swatch", style: `background:${colour}` });
  }

  function avatar(person, small) {
    const cls = "avatar" + (small ? " small" : "");
    if (person.login) {
      return el("img", {
        class: cls, alt: "", loading: "lazy", width: small ? 20 : 32, height: small ? 20 : 32,
        src: `https://github.com/${encodeURIComponent(person.login)}.png?size=64`,
      });
    }
    const initials = (person.name || "?").split(/\s+/).map((word) => word[0]).slice(0, 2).join("").toUpperCase();
    return el("span", { class: cls + " initials", "aria-hidden": "true", text: initials });
  }

  function profile(login) {
    return `https://github.com/${encodeURIComponent(login)}`;
  }

  /* ---------- Tooltip ---------- */

  function showTooltip(event, title, rows) {
    tooltip.replaceChildren(
      el("div", { class: "tt-title", text: title }),
      ...rows.map((row) =>
        el("div", { class: "tt-row" },
          row.colour ? el("span", { class: "key", style: `background:${row.colour}` }) : null,
          el("span", { class: "v", text: row.value }),
          el("span", { class: "n", text: row.name }))),
    );
    tooltip.hidden = false;
    const box = tooltip.getBoundingClientRect();
    let x = event.clientX + 14;
    if (x + box.width > window.innerWidth - 8) x = event.clientX - box.width - 14;
    const y = Math.min(Math.max(8, event.clientY - box.height / 2), window.innerHeight - box.height - 8);
    tooltip.style.left = Math.max(8, x) + "px";
    tooltip.style.top = y + "px";
  }

  function hideTooltip() {
    tooltip.hidden = true;
  }

  /* ---------- Sections ---------- */

  function intro(report) {
    const project = report.project;
    const totals = report.totals;
    return el("div", { class: "intro" },
      el("h1", { text: project.name }),
      el("p", {
        text: `What the contributors of ${project.name} declare about their use of AI tools, ` +
          `read from ${number.format(totals.commits)} commits` +
          (report.pulls ? ` and ${plural(report.pulls.items.length, "pull request")}` : "") +
          `, from ${day(totals.first)} to ${day(totals.last)}.`,
      }),
      el("div", { class: "links" },
        el("a", { href: project.url, target: "_blank", rel: "noreferrer", text: project.repository }),
        project.policy_url ? el("a", { href: project.policy_url, target: "_blank", rel: "noreferrer", text: "The project's rules on AI-assisted contributions" }) : null,
        el("a", { href: "#reading", text: "How to read these figures" })),
    );
  }

  function tiles(report) {
    const totals = report.totals;
    const since = report.project.trailer_since;
    const vendors = new Set(report.models.filter((model) => !model.tool).map((model) => model.vendor)).size;
    const hero = since
      ? {
          label: `Commits declaring an AI model since ${day(since)}`,
          part: totals.since_ai_commits, whole: totals.since_commits,
          note: "by people, since the trailer is required",
        }
      : { label: "Commits declaring an AI model", part: totals.ai_commits, whole: totals.human_commits, note: "by people" };

    return el("div", { class: "tiles" },
      el("div", { class: "tile hero" },
        el("div", { class: "label", text: hero.label }),
        el("div", { class: "value", text: percent(hero.part, hero.whole) }),
        el("div", { class: "note", text: `${number.format(hero.part)} of ${plural(hero.whole, "commit")} ${hero.note}` }),
        el("div", { class: "meter", role: "img", "aria-label": `${percent(hero.part, hero.whole)} of commits` },
          el("span", { style: `width:${hero.whole ? (100 * hero.part) / hero.whole : 0}%` }))),
      el("div", { class: "tile" },
        el("div", { class: "label", text: "Over the whole history" }),
        el("div", { class: "value", text: percent(totals.ai_commits, totals.human_commits) }),
        el("div", { class: "note", text: `${number.format(totals.ai_commits)} of ${number.format(totals.human_commits)} commits by people declare a model` })),
      report.lines ? el("div", { class: "tile" },
        el("div", { class: "label", text: "Lines changed, in commits declaring a model" }),
        el("div", { class: "value", text: percent(report.lines.named, report.lines.changed) }),
        el("div", { class: "note", text: `${compact.format(report.lines.named)} of ${compact.format(report.lines.changed)} lines changed by people` +
          (since && report.lines.since_changed ? ` · ${percent(report.lines.since_named, report.lines.since_changed)} since ${day(since)}` : "") })) : null,
      el("div", { class: "tile" },
        el("div", { class: "label", text: "Contributors" }),
        el("div", { class: "value", text: number.format(totals.humans) }),
        el("div", { class: "note", text: `${number.format(totals.humans_with_ai)} declared a model at least once` })),
      el("div", { class: "tile" },
        el("div", { class: "label", text: "Models named" }),
        el("div", { class: "value", text: number.format(totals.models) }),
        el("div", { class: "note", text: `from ${plural(vendors, "vendor")}` +
          (totals.tools ? ` · and ${plural(totals.tools, "tool")} whose model is not named` : "") })),
      report.pulls ? pullTile(report.pulls) : null,
    );
  }

  function pullTile(pulls) {
    const judged = pulls.items.filter((item) => item.boxes.human !== undefined && item.boxes.human !== "not-yet");
    const ticked = judged.filter((item) => item.boxes.human === "ticked").length;
    return el("div", { class: "tile" },
      el("div", { class: "label", text: "Pull requests stating “read, understood and tested”" }),
      el("div", { class: "value", text: `${number.format(ticked)} of ${number.format(judged.length)}` }),
      el("div", { class: "note", text: `opened by people since ${day(pulls.since)}` }));
  }

  const COMMITS = {
    id: "commits", title: "Commits per month", unit: "Commits", total: "commits in all",
    aria: "Commits per month, by declared model family. The table below gives the same figures.",
    sub: "Each commit is counted under the model its Co-Authored-By trailer names, or as “no AI declared”. Commits by dependency-update bots are left out.",
    pick: (month) => month,
  };

  const LINES = {
    id: "lines", title: "Lines changed per month", unit: "Lines", total: "lines in all", compact: true,
    aria: "Lines changed per month, by the model family the commits name. The table below gives the same figures.",
    sub: "The lines each commit adds and deletes, counted under the model its trailer names, or as “no AI declared”. These are the lines of commits that name a model, not lines written by a model: a person may have written part of such a commit, or all of it.",
    pick: (month) => month.lines,
  };

  // The same chart for commits and for lines: what is counted comes from the configuration.
  function timeline(report, palette, config, after) {
    const series = [...report.families.map((family) => family.id), ...(config.none === false ? [] : [NONE])];
    const months = report.months.map((month) => {
      const counted = config.pick(month);
      const values = { ...counted.families, [NONE]: counted.none };
      const total = series.reduce((sum, id) => sum + (values[id] || 0), 0);
      return { key: month.month, values, total };
    });
    let mode = "count";
    const holder = el("div", { class: "chart" });

    function draw() {
      const width = Math.max(320, Math.floor(holder.clientWidth || 960));
      const height = 300;
      const margin = { top: 26, right: 8, bottom: 26, left: 40 };
      const plotW = width - margin.left - margin.right;
      const plotH = height - margin.top - margin.bottom;
      const peak = mode === "share" ? 100 : Math.max(1, ...months.map((month) => month.total));
      const step = niceStep(peak / 4);
      const top = mode === "share" ? 100 : Math.ceil(peak / step) * step;
      const band = plotW / months.length;
      const barW = Math.max(2, Math.min(24, band - 2));
      const y = (value) => margin.top + plotH - (value / top) * plotH;

      const chart = svg("svg", { viewBox: `0 0 ${width} ${height}`, role: "img",
        "aria-label": config.aria });

      for (let tick = 0; tick <= top + 1e-9; tick += step) {
        chart.append(svg("line", { class: tick ? "grid" : "axis", x1: margin.left, x2: width - margin.right, y1: y(tick), y2: y(tick) }));
        const label = svg("text", { x: margin.left - 8, y: y(tick) + 4, "text-anchor": "end" });
        label.textContent = mode === "share" ? tick + "%" : (config.compact ? compact : number).format(tick);
        chart.append(label);
      }

      // A year label under each January, or under the first month.
      const everyYear = band * 12 >= 34;
      months.forEach((month, index) => {
        const [year, mm] = month.key.split("-");
        if (mm !== "01" && index !== 0) return;
        if (index === 0 && mm !== "01" && (12 - Number(mm) + 1) * band < 34) return;
        if (!everyYear && Number(year) % 2) return;
        const label = svg("text", { x: margin.left + index * band + band / 2, y: height - 8, "text-anchor": "middle" });
        label.textContent = year;
        chart.append(label);
      });

      const bands = [];
      months.forEach((month, index) => {
        const x = margin.left + index * band + (band - barW) / 2;
        let base = 0;
        const present = series.filter((id) => month.values[id]);
        present.forEach((id, position) => {
          const value = mode === "share" ? (100 * month.values[id]) / month.total : month.values[id];
          const y0 = y(base);
          const y1 = y(base + value);
          base += value;
          const last = position === present.length - 1;
          const gap = last || y0 - y1 < 4 ? 0 : 2; // the surface shows between two segments
          const h = Math.max(0.5, y0 - y1 - gap);
          const r = last ? Math.min(4, barW / 2, h) : 0;
          const yTop = y0 - h;
          chart.append(svg("path", {
            fill: palette.get(id),
            d: `M${x},${y0}V${yTop + r}q0,${-r} ${r},${-r}h${barW - 2 * r}q${r},0 ${r},${r}V${y0}Z`,
          }));
        });

        const hit = svg("rect", { class: "band", x: margin.left + index * band, y: margin.top, width: band, height: plotH });
        hit.addEventListener("pointermove", (event) => {
          bands.forEach((other) => other.classList.toggle("active", other === hit));
          showTooltip(event, monthName(month.key), [
            ...series.filter((id) => month.values[id]).reverse().map((id) => ({
              colour: palette.get(id), name: id,
              value: number.format(month.values[id]) + (mode === "share" ? ` · ${percent(month.values[id], month.total)}` : ""),
            })),
            { name: config.total, value: number.format(month.total) },
          ]);
        });
        hit.addEventListener("pointerleave", () => { hit.classList.remove("active"); hideTooltip(); });
        bands.push(hit);
      });

      const since = report.project && report.project.trailer_since;
      const start = months.findIndex((month) => month.key === (since || "").slice(0, 7));
      if (start >= 0) {
        const days = new Date(Date.UTC(Number(since.slice(0, 4)), Number(since.slice(5, 7)), 0)).getUTCDate();
        const x = margin.left + start * band + (band * (Number(since.slice(8, 10)) - 1)) / days;
        chart.append(svg("line", { class: "marker", x1: x, x2: x, y1: margin.top - 8, y2: margin.top + plotH }));
        const label = svg("text", { class: "marker-label", x: x - 6, y: margin.top - 12, "text-anchor": "end" });
        label.textContent = `Trailer required from ${day(since)}`;
        chart.append(label);
      }

      bands.forEach((hit) => chart.append(hit));
      holder.replaceChildren(chart);
    }

    const buttons = [["count", config.unit], ["share", "Share"]].map(([value, label]) =>
      el("button", {
        type: "button", "aria-pressed": String(value === mode), text: label,
        onclick: () => {
          mode = value;
          buttons.forEach((button, index) => button.setAttribute("aria-pressed", String(["count", "share"][index] === mode)));
          draw();
        },
      }));

    const table = el("table", {},
      el("thead", {}, el("tr", {}, el("th", { text: "Month" }), series.map((id) => el("th", { class: "num", text: id })), el("th", { class: "num", text: "All" }))),
      el("tbody", {}, [...months].reverse().map((month) =>
        el("tr", {}, el("td", { text: monthName(month.key) }),
          series.map((id) => el("td", { class: "num", text: number.format(month.values[id] || 0) })),
          el("td", { class: "num", text: number.format(month.total) })))));

    const section = el("section", { id: config.id },
      el("h2", { text: config.title }),
      el("p", { class: "sub", text: config.sub }),
      el("div", { class: "card" },
        el("div", { class: "chart-head" },
          el("ul", { class: "legend" }, series.map((id) => el("li", {}, swatch(palette.get(id)), id))),
          el("div", { class: "toggle", role: "group", "aria-label": "Unit" }, buttons)),
        holder,
        el("details", { class: "table-view" }, el("summary", { text: "Show as a table" }), el("div", { class: "table-scroll" }, table))),
      after || null);

    new ResizeObserver(draw).observe(holder);
    return section;
  }

  function lines(report, palette) {
    const data = report.lines;
    if (!data) return null;
    const weight = data.heaviest.reduce((sum, item) => sum + item.lines, 0);
    const heaviest = data.heaviest.length ? el("div", { class: "heaviest" },
      el("p", { text: `A few commits can weigh a lot: a data file, a library copied into the project, a renamed directory. ` +
        `The ${data.heaviest.length === 1 ? "largest commit makes" : data.heaviest.length + " largest commits make"} up ${percent(weight, data.charted)} of all the lines above.` }),
      el("ol", {}, data.heaviest.map((item) =>
        el("li", {},
          el("span", { class: "num", text: number.format(item.lines) }),
          el("span", {},
            el("a", { href: `${report.project.url}/commit/${item.sha}`, text: item.title || item.sha.slice(0, 10) }),
            el("small", {}, ` ${day(item.date)} · `, swatch(palette.get(item.family || NONE)), item.family || NONE)))))) : null;
    const unknown = data.unknown_commits
      ? el("p", { class: "sub after", text: `GitHub gave no figure for ${plural(data.unknown_commits, "commit")}: counted as no line.` })
      : null;
    return timeline(report, palette, LINES, [heaviest, unknown]);
  }

  // A year of days, one column per week: how many commits name a model each day.
  function calendar(days, last, sub) {
    const DAY = 86400000;
    const stamp = (iso) => Date.UTC(Number(iso.slice(0, 4)), Number(iso.slice(5, 7)) - 1, Number(iso.slice(8, 10)));
    const iso = (moment) => new Date(moment).toISOString().slice(0, 10);
    const end = stamp(last);
    // 53 columns, the first one starting on a Monday.
    let start = end - 52 * 7 * DAY;
    start -= ((new Date(start).getUTCDay() + 6) % 7) * DAY;
    const cells = [];
    for (let moment = start; moment <= end; moment += DAY) cells.push({ day: iso(moment), count: days[iso(moment)] || 0 });
    const total = cells.reduce((sum, cell) => sum + cell.count, 0);
    if (!total) return null;
    const peak = Math.max(...cells.map((cell) => cell.count));
    const level = (count) => (count ? Math.min(4, Math.ceil((4 * count) / peak)) : 0);

    const size = 15, pitch = 18, left = 32, top = 18;
    const columns = Math.ceil(cells.length / 7);
    const width = left + columns * pitch, height = top + 7 * pitch;
    const chart = svg("svg", { width, height, viewBox: `0 0 ${width} ${height}`, role: "img",
      "aria-label": `${plural(total, "commit")} naming a model on ${plural(cells.filter((cell) => cell.count).length, "day")}, from ${day(cells[0].day)} to ${day(last)}.` });
    ["Mon", "Wed", "Fri"].forEach((name, index) => {
      const label = svg("text", { x: 0, y: top + index * 2 * pitch + size - 1 });
      label.textContent = name;
      chart.append(label);
    });
    cells.forEach((cell, index) => {
      const column = Math.floor(index / 7), row = index % 7;
      if (row === 0 || index === 0) {
        // The name of a month above the first column that starts in it.
        const previous = index >= 7 ? cells[index - 7].day.slice(0, 7) : "";
        if (cell.day.slice(0, 7) !== previous && column < columns - 1) {
          const label = svg("text", { x: left + column * pitch, y: 10 });
          label.textContent = new Date(stamp(cell.day)).toLocaleDateString("en-GB", { month: "short", timeZone: "UTC" });
          chart.append(label);
        }
      }
      const square = svg("rect", { class: `cal-${level(cell.count)}`, x: left + column * pitch, y: top + row * pitch, width: size, height: size, rx: 2 });
      square.addEventListener("pointermove", (event) =>
        showTooltip(event, day(cell.day), [{ name: cell.count === 1 ? "commit naming a model" : "commits naming a model", value: number.format(cell.count) }]));
      square.addEventListener("pointerleave", hideTooltip);
      chart.append(square);
    });
    const scroll = el("div", { class: "calendar-scroll" }, chart);
    // On a narrow screen, show the latest weeks first.
    requestAnimationFrame(() => { scroll.scrollLeft = scroll.scrollWidth; });
    return el("section", { id: "calendar" },
      el("h2", { text: "Day by day" }),
      el("p", { class: "sub", text: sub }),
      el("div", { class: "card calendar" }, scroll,
        el("div", { class: "calendar-legend", "aria-hidden": "true" }, "Fewer",
          [0, 1, 2, 3, 4].map((step) => { const key = svg("svg", { width: 11, height: 11 }); key.append(svg("rect", { class: `cal-${step}`, width: 11, height: 11, rx: 2 })); return key; }),
          "More")));
  }

  function niceStep(raw) {
    const power = Math.pow(10, Math.floor(Math.log10(Math.max(raw, 1))));
    const unit = raw / power;
    return Math.max(1, (unit <= 1 ? 1 : unit <= 2 ? 2 : unit <= 5 ? 5 : 10) * power);
  }

  function models(report, palette) {
    const peak = Math.max(1, ...report.models.map((model) => model.commits));
    const rows = report.models.flatMap((model) => {
      const period = model.first.slice(0, 7) === model.last.slice(0, 7)
        ? day(model.first.slice(0, 7))
        : `${day(model.first.slice(0, 7))} – ${day(model.last.slice(0, 7))}`;
      const title = `${model.label}: ${plural(model.commits, "commit")}` +
        (report.lines ? `, ${plural(model.lines, "line")} changed` : "");
      return [
        el("div", { class: "name" }, swatch(palette.get(model.family)),
          el("span", {}, model.label, el("small", { text: `${model.vendor} · ${model.tool ? TOOL + " · " : ""}${period}` }))),
        el("div", { class: "figure" }, number.format(model.commits),
          el("small", { text: model.people ? ` · ${plural(model.people, "person", "people")}` : "" })),
        el("div", { class: "track", title },
          el("div", { class: "bar", style: `width:${(100 * model.commits) / peak}%;background:${palette.get(model.family)}` })),
      ];
    });
    return el("section", { id: "models" },
      el("h2", { text: "Models and versions" }),
      el("p", { class: "sub", text: "Commits naming each model, with the months it was in use and the number of people who named it. Spellings of one model are counted together." }),
      el("div", { class: "card" }, rows.length ? el("div", { class: "bars" }, rows) : el("p", { class: "empty", text: "No commit names a model yet." })));
  }

  function split(person, palette, families) {
    const parts = [...families.filter((id) => person.families[id]).map((id) => [id, person.families[id]]),
      [NONE, person.commits - person.ai_commits]].filter(([, count]) => count > 0);
    const description = parts.map(([id, count]) => `${id}: ${number.format(count)}`).join(", ");
    return el("div", { class: "split", role: "img", "aria-label": description, title: description },
      parts.map(([id, count]) => el("span", { style: `flex:${count} 1 0;background:${palette.get(id)}` })));
  }

  function contributors(report, palette) {
    const since = report.project.trailer_since;
    const families = report.families.map((family) => family.id);
    let filter = "all";
    const body = el("tbody");
    const count = el("span", { class: "empty" });

    function fill() {
      const people = report.contributors.filter((person) =>
        filter === "all" || (filter === "ai") === (person.ai_commits > 0));
      count.textContent = plural(people.length, "contributor");
      body.replaceChildren(...people.map((person) =>
        el("tr", {},
          el("td", {}, el("div", { class: "person" }, avatar(person),
            el("span", {},
              person.login ? el("a", { href: profile(person.login), text: person.name }) : el("strong", { text: person.name }),
              el("small", { text: person.login ? "@" + person.login : "no GitHub account matched" })))),
          el("td", { class: "num", text: number.format(person.commits),
            title: report.lines ? `${plural(person.lines, "line")} changed, ${number.format(person.ai_lines)} in commits declaring a model` : null }),
          el("td", { class: "num" }, number.format(person.ai_commits), " ", el("small", { text: percent(person.ai_commits, person.commits) })),
          el("td", {}, split(person, palette, families)),
          since ? el("td", { class: "num" }, person.since_commits
            ? `${number.format(person.since_ai_commits)} of ${number.format(person.since_commits)}`
            : el("small", { text: "no commit" })) : null,
          el("td", { class: "models-used", text: person.models.length
            ? person.models.map((model) => `${model.label} (${number.format(model.commits)})`).join(", ")
            : NONE }),
          el("td", {}, el("small", { text: `${person.first.slice(0, 4)}${person.first.slice(0, 4) === person.last.slice(0, 4) ? "" : "–" + person.last.slice(0, 4)}` })))));
    }

    const options = [["all", "Everyone"], ["ai", "Declared a model"], ["none", NONE]];
    const buttons = options.map(([value, label]) =>
      el("button", {
        type: "button", "aria-pressed": String(value === filter), text: label,
        onclick: () => {
          filter = value;
          buttons.forEach((button, index) => button.setAttribute("aria-pressed", String(options[index][0] === filter)));
          fill();
        },
      }));
    fill();

    const others = report.others.length
      ? el("p", { class: "empty", style: "margin:16px 0 0" },
          "Not people: ",
          report.others.map((other) =>
            `${other.name} (${plural(other.commits, "commit")}, ${other.kind === "agent" ? "an AI agent with no human co-author" : "automation"})`).join("; "),
          ".")
      : null;

    return el("section", { id: "contributors" },
      el("h2", { text: "Contributors" }),
      el("p", { class: "sub", text: "Who declares which model. “No AI declared” means that no commit of the person names a model: it does not show that no AI tool was used." }),
      el("div", { class: "card" },
        el("div", { class: "filters" }, el("div", { class: "toggle", role: "group", "aria-label": "Contributors shown" }, buttons), count),
        el("div", { class: "table-scroll" },
          el("table", {},
            el("thead", {}, el("tr", {},
              el("th", { text: "Contributor" }),
              el("th", { class: "num", text: "Commits" }),
              el("th", { class: "num", text: "Declaring a model" }),
              el("th", { text: "Split" }),
              since ? el("th", { class: "num", text: `Since ${day(since)}` }) : null,
              el("th", { text: "Models named" }),
              el("th", { text: "Active" }))),
            body)),
        others));
  }

  const BOX = {
    ticked: ["✓", "ticked"],
    unticked: ["☐", "not ticked"],
    missing: ["–", "box removed"],
    "not-yet": ["", "not asked yet"],
  };

  const READING = {
    "consistent-ai": ["ok", "✓", "Box and commits agree"],
    "consistent-none": ["ok", "✓", NONE],
    "box-without-trailer": ["check", "!", "Box ticked, no model named"],
    "trailer-without-box": ["check", "!", "Model named, box not ticked"],
    "template-missing": ["check", "!", "Template not filled in"],
    trailers: ["ok", "·", "Commits name a model"],
    none: ["ok", "·", NONE],
  };

  function box(state) {
    const [mark, label] = BOX[state] || BOX.missing;
    return el("span", { class: "box " + state }, el("span", { class: "mark", "aria-hidden": "true", text: mark }), label);
  }

  function pulls(report) {
    const data = report.pulls;
    if (!data) {
      return el("section", { id: "pulls" },
        el("h2", { text: "Pull requests" }),
        el("p", { class: "empty", text: report.github
          ? "No box of the pull request template is followed for this project."
          : "This report was built without access to GitHub: pull requests were not read." }));
    }
    const items = data.items;
    const agree = items.filter((item) => READING[item.disclosure][0] === "ok").length;
    const boxes = data.checkboxes;

    const rows = items.map((item) => {
      const [kind, mark, label] = READING[item.disclosure];
      const commits = item.model_commits
        ? `${number.format(item.model_commits)} of ${number.format(item.commits_read)}`
        : `0 of ${number.format(item.commits_read)}`;
      return el("tr", {},
        el("td", { class: "pr-title" }, el("a", { href: item.url, text: `#${item.number}` }), " ", item.title,
          " ", el("span", { class: "state", text: item.state })),
        el("td", {}, el("div", { class: "person", style: "min-width:0" }, avatar({ login: item.author, name: item.author }, true),
          item.author ? el("a", { href: profile(item.author), text: item.author }) : "unknown")),
        el("td", { class: "num", text: day(item.opened) }),
        boxes.map((entry) => el("td", {}, box(item.boxes[entry.id]))),
        el("td", {}, commits, item.models.length ? el("small", { text: " · " + item.models.join(", ") }) : null,
          item.commits > item.commits_read ? el("small", { text: ` (first ${item.commits_read} of ${item.commits})` }) : null),
        el("td", {}, el("span", { class: "reading " + kind }, el("span", { class: "mark", "aria-hidden": "true", text: mark }), label)));
    });

    return el("section", { id: "pulls" },
      el("h2", { text: "Pull requests" }),
      el("p", { class: "sub", text: `Pull requests opened by people since ${day(data.since)}, when the template started to ask about AI. ` +
        "The boxes of each description are compared with the trailers of its commits." +
        (data.skipped_bots ? ` ${plural(data.skipped_bots, "pull request")} opened by bots left out.` : "") }),
      el("div", { class: "card" },
        items.length
          ? [el("p", { class: "empty", style: "margin:0 0 12px", text: `In ${number.format(agree)} of ${plural(items.length, "pull request")}, the description and the commits tell the same story.` }),
             el("div", { class: "table-scroll" },
               el("table", {},
                 el("thead", {}, el("tr", {},
                   el("th", { text: "Pull request" }), el("th", { text: "Author" }), el("th", { class: "num", text: "Opened" }),
                   boxes.map((entry) => el("th", { text: "Box: " + entry.label })),
                   el("th", { text: "Commits naming a model" }), el("th", { text: "Box and commits" }))),
                 el("tbody", {}, rows)))]
          : el("p", { class: "empty", text: "No pull request opened since that date." })));
  }

  function film(report) {
    if (!report.video) return null;
    const video = el("video", { class: "film", controls: "", preload: "none", playsinline: "" });
    video.src = report.video.file;
    if (report.video.poster) video.poster = report.video.poster;
    return el("section", { id: "film" },
      el("h2", { text: "The history, in motion" }),
      el("p", { class: "sub", text: "Every commit of the project, drawn with Gource. Each person works on the files of their commits; when a commit names a model, the model family works on the same files beside them." }),
      el("div", { class: "card" }, video),
      el("p", { class: "sub film-note", text: "A file keeps the colour of its type, whoever changed it: a trailer says that a model took part in a commit, not how much of a file it wrote. Automated accounts are left out." }));
  }

  function badgeSection(report) {
    const slug = encodeURIComponent(report.project.slug);
    const image = new URL(`badge/${slug}.svg`, location.href).href;
    const page = new URL(`?project=${slug}`, location.href).href;
    return el("section", { id: "badge" },
      el("h2", { text: "Badge" }),
      el("p", { class: "sub", text: `A small image that says the same as the first figure of this page, rebuilt with it. ${report.project.name} can show it in its README:` }),
      el("div", { class: "card badge" },
        el("img", { src: `badge/${slug}.svg`, alt: "The badge of the project", height: 20 }),
        el("pre", {}, el("code", { text: `[![AI use](${image})](${page})` }))));
  }

  function reading(report) {
    const since = report.project.trailer_since;
    return el("section", { id: "reading" },
      el("h2", { text: "How to read these figures" }),
      el("ul", { class: "notes" },
        el("li", { text: "A commit “declares a model” when a Co-Authored-By trailer of its message names an AI model, or when an AI agent is its author. A commit authored by an agent is credited to the person named as its co-author." }),
        el("li", { text: "“No AI declared” is exactly that. Nothing here can show that a commit was written without an AI tool." }),
        report.models.some((model) => model.tool) ? el("li", { text: TOOL_NOTE }) : null,
        report.lines ? el("li", { text: "“Lines changed” are the lines a commit adds plus the lines it deletes, as GitHub counts them. A commit that names a model counts in full, whoever wrote each line, and a generated file or a data file counts like any other." }) : null,
        since ? el("li", { text: `The project requires the trailer since ${day(since)}. Earlier commits are shown for the history and are not held to a rule that did not exist.` }) : null,
        el("li", { text: "Merge commits are not counted. People are recognised by their GitHub account, so that several e-mail addresses of one person count together; e-mail addresses are not published." }),
        el("li", { text: "For a pull request, “box removed” means that the line of the template is not in the description. The “read, understood and tested” box is the author's own statement: an AI tool must leave it unticked." }),
        el("li", { text: "This page takes no side on the use of AI. It exists so that the use is said, not to rank anyone." })));
  }

  /* ---------- Loading ---------- */

  function render(report) {
    const palette = colours(report);
    document.title = `${report.project.name} · AI transparency for Open Source projects`;
    root.replaceChildren(...[
      intro(report), tiles(report), timeline(report, palette, COMMITS),
      calendar(report.named.days, report.generated_at.slice(0, 10), "Commits naming a model on each day of the last year. A stronger blue is a day with more of them; a pale one is a day with no model named, not a day without work."),
      models(report, palette), lines(report, palette),
      contributors(report, palette), pulls(report), film(report), badgeSection(report), reading(report)].filter(Boolean));
    anchor();
    document.getElementById("footer").textContent =
      `Built on ${day(report.generated_at.slice(0, 10))} from the public history of ${report.project.repository}.`;
  }

  // The sections did not exist when the browser looked for the anchor of the address.
  function anchor() {
    const target = location.hash.length > 1 && document.getElementById(decodeURIComponent(location.hash.slice(1)));
    if (!target) return;
    // The page keeps changing height for a moment (the chart is drawn, the font
    // arrives): follow it, until the reader starts to scroll.
    const follow = new ResizeObserver(() => target.scrollIntoView({ behavior: "instant" }));
    const stop = () => follow.disconnect();
    ["wheel", "touchstart", "keydown", "mousedown"].forEach((kind) =>
      addEventListener(kind, stop, { once: true, passive: true }));
    setTimeout(stop, 5000);
    follow.observe(root);
  }

  /* ---------- Statistics of all the projects ---------- */

  const NAMED = {
    id: "time", title: "Models named, month by month", unit: "Commits", total: "commits naming a model", none: false,
    aria: "Commits naming a model per month, by model family, all projects together. The table below gives the same figures.",
    sub: "Commits naming a model, all projects together, under the family of the model. A commit that names several models is counted once, under the first one. “Share” shows one family taking over from another.",
    pick: (month) => month,
  };

  function period(first, last) {
    const from = first.slice(0, 7);
    const to = last.slice(0, 7);
    return from === to ? day(from) : `${day(from)} – ${day(to)}`;
  }

  function statsIntro(stats) {
    return el("div", { class: "intro" },
      el("h1", { text: "Statistics" }),
      el("p", { text: `Which AI models contributors name in their commits, in the ${plural(stats.projects, "project")} followed here, all together. ` +
        "No project and no person is named on this page: it is not a ranking." }),
      el("div", { class: "links" },
        el("a", { href: "#models", text: "Models named the most" }),
        el("a", { href: "#time", text: "Month by month" }),
        el("a", { href: "#lifetimes", text: "Life of a version" }),
        el("a", { href: "#vendors", text: "Vendors" }),
        el("a", { href: "#spread", text: "How declaring spread" }),
        el("a", { href: "#reading", text: "How to read these figures" })));
  }

  function statsTiles(stats) {
    const totals = stats.totals;
    const tile = (label, value, note) => el("div", { class: "tile" },
      el("div", { class: "label", text: label }),
      el("div", { class: "value", text: value }),
      el("div", { class: "note", text: note }));
    return el("div", { class: "tiles" },
      tile("Commits naming a model", number.format(totals.commits),
        totals.first ? `the first one on ${day(totals.first)}` : "none yet"),
      totals.lines === null ? null : tile("Lines changed in those commits", compact.format(totals.lines),
        "lines of commits that name a model, not lines written by a model" +
        (totals.lines_projects < stats.projects ? ` · known for ${totals.lines_projects} of ${plural(stats.projects, "project")}` : "")),
      tile("People who named a model", number.format(totals.people), "at least once, in a commit of theirs"),
      tile("Commits naming several models", number.format(totals.several),
        `${percent(totals.several, totals.commits)} of the commits naming a model`),
      tile("Models named", number.format(totals.models),
        `${plural(totals.families, "family", "families")} from ${plural(totals.vendors, "vendor")}` +
        (totals.tools ? ` · and ${plural(totals.tools, "tool")} whose model is not named` : "")));
  }

  // Ranked bars: [{ name, small, colour, value, figureSmall, title }].
  function bars(rows) {
    const peak = Math.max(1, ...rows.map((row) => row.value));
    return el("div", { class: "bars" }, rows.flatMap((row) => [
      el("div", { class: "name" }, row.colour ? swatch(row.colour) : null,
        el("span", {}, row.name, row.small ? el("small", { text: row.small }) : null)),
      el("div", { class: "figure" }, number.format(row.value), row.figureSmall ? el("small", { text: " · " + row.figureSmall }) : null),
      el("div", { class: "track", title: row.title },
        row.value ? el("div", { class: "bar", style: `width:${(100 * row.value) / peak}%;background:${row.colour || "var(--ink-2)"}` }) : null),
    ]));
  }

  function mostNamed(stats, palette) {
    const views = {
      family: () => stats.families.map((family) => ({
        name: family.id, small: family.vendor + (family.tool ? " · " + TOOL : ""), colour: palette.get(family.id), value: family.commits,
        figureSmall: percent(family.commits, stats.totals.commits),
        title: `${family.id}: ${plural(family.commits, "commit")}`,
      })),
      version: () => stats.models.map((model) => ({
        name: model.label, small: `${model.vendor} · ${model.tool ? TOOL + " · " : ""}${period(model.first, model.last)}`,
        colour: palette.get(model.family), value: model.commits,
        title: `${model.label}: ${plural(model.commits, "commit")}` +
          (stats.totals.lines === null ? "" : `, ${plural(model.lines, "line")} changed`),
      })),
    };
    const notes = {
      family: "Each commit is counted once, under the family of the first model it names.",
      version: "A commit that names several models counts for each of them, so this list adds up to a little more than the commits.",
    };
    let view = "family";
    const holder = el("div");
    const note = el("p", { class: "sub after" });
    const options = [["family", "Families"], ["version", "Versions"]];
    const fill = () => {
      holder.replaceChildren(bars(views[view]()));
      note.textContent = notes[view];
    };
    const buttons = options.map(([value, label]) =>
      el("button", {
        type: "button", "aria-pressed": String(value === view), text: label,
        onclick: () => {
          view = value;
          buttons.forEach((button, index) => button.setAttribute("aria-pressed", String(options[index][0] === view)));
          fill();
        },
      }));
    fill();
    return el("section", { id: "models" },
      el("h2", { text: "Models named the most" }),
      el("p", { class: "sub", text: "Commits naming each model, all projects together. Spellings of one model are counted together." }),
      el("div", { class: "card" },
        el("div", { class: "filters" }, el("div", { class: "toggle", role: "group", "aria-label": "Grouping" }, buttons)),
        holder),
      note);
  }

  function lifetimes(stats, palette) {
    const time = (iso) => Date.UTC(Number(iso.slice(0, 4)), Number(iso.slice(5, 7)) - 1, Number(iso.slice(8, 10)) || 1);
    const models = stats.models.filter((model) => !model.tool).sort((a, b) => a.first.localeCompare(b.first) || a.label.localeCompare(b.label));
    if (!models.length) return null;
    const first = models[0].first;
    const start = time(first.slice(0, 7));
    const end = Math.max(time(stats.totals.last), start + 86400000);
    const place = (moment) => (100 * (moment - start)) / (end - start);

    // A mark at each January, or at each quarter when the history is short.
    const stride = end - start > 2 * 365 * 86400000 ? 12 : 3;
    let marks = [];
    for (let year = Number(first.slice(0, 4)), month = 0; Date.UTC(year, month, 1) <= end; month += stride) {
      const moment = Date.UTC(year, month, 1);
      if (moment >= start) marks.push({ at: place(moment), label: stride === 12 ? String(year + month / 12) : day(new Date(moment).toISOString().slice(0, 7)) });
    }
    while (marks.length > 6) marks = marks.filter((_, index) => index % 2 === 0);
    const ruler = () => marks.map((mark) => el("span", { class: "mark", style: `left:${mark.at}%` }));

    const rows = models.flatMap((model) => {
      const left = place(time(model.first));
      const width = Math.max(0, place(time(model.last)) - left);
      return [
        el("div", { class: "name" }, swatch(palette.get(model.family)), el("span", { text: model.label })),
        el("div", { class: "figure" }, el("small", { text: period(model.first, model.last) })),
        el("div", { class: "track span", title: `${model.label}: named from ${day(model.first)} to ${day(model.last)}, in ${plural(model.commits, "commit")}` },
          ruler(),
          el("div", { class: "bar", style: `left:${left}%;width:${width}%;background:${palette.get(model.family)}` })),
      ];
    });
    const scale = el("div", { class: "track scale", "aria-hidden": "true" },
      marks.map((mark) => el("span", { style: `left:${mark.at}%`, text: mark.label })));

    return el("section", { id: "lifetimes" },
      el("h2", { text: "Life of a model version" }),
      el("p", { class: "sub", text: "From the first to the last commit naming each version, all projects together. A bar says when a version was named, not how often." +
        (stats.totals.tools ? " Tools whose model is not named are left out: nothing says which versions they ran on." : "") }),
      el("div", { class: "card" }, rows.length
        ? el("div", { class: "bars spans" }, rows, scale)
        : el("p", { class: "empty", text: "No commit names a model yet." })));
  }

  // Two step lines: the projects and the people who have named a model so far.
  function spread(stats) {
    const months = stats.spread;
    const series = [
      { id: "people", name: "People", one: "person", many: "people", colour: "var(--ink)", dash: null },
      { id: "projects", name: "Projects", one: "project", many: "projects", colour: "var(--ink-2)", dash: "5 4" },
    ];
    const holder = el("div", { class: "chart" });

    function draw() {
      const width = Math.max(320, Math.floor(holder.clientWidth || 960));
      const height = 260;
      const margin = { top: 16, right: 92, bottom: 26, left: 40 };
      const plotW = width - margin.left - margin.right;
      const plotH = height - margin.top - margin.bottom;
      const peak = Math.max(1, ...months.map((month) => Math.max(month.people, month.projects)));
      const step = niceStep(peak / 4);
      const top = Math.ceil(peak / step) * step;
      const band = plotW / months.length;
      const y = (value) => margin.top + plotH - (value / top) * plotH;
      const chart = svg("svg", { viewBox: `0 0 ${width} ${height}`, role: "img",
        "aria-label": "Projects and people with at least one commit naming a model, month by month. The table below gives the same figures." });

      for (let tick = 0; tick <= top + 1e-9; tick += step) {
        chart.append(svg("line", { class: tick ? "grid" : "axis", x1: margin.left, x2: margin.left + plotW, y1: y(tick), y2: y(tick) }));
        const label = svg("text", { x: margin.left - 8, y: y(tick) + 4, "text-anchor": "end" });
        label.textContent = number.format(tick);
        chart.append(label);
      }
      months.forEach((month, index) => {
        const [year, mm] = month.month.split("-");
        if (mm !== "01" && index !== 0) return;
        if (index === 0 && mm !== "01" && (12 - Number(mm) + 1) * band < 34) return;
        const label = svg("text", { x: margin.left + index * band + band / 2, y: height - 8, "text-anchor": "middle" });
        label.textContent = year;
        chart.append(label);
      });

      // The labels at the end of the lines must not sit on each other.
      const ends = series.map((entry) => ({ entry, value: months[months.length - 1][entry.id] }));
      const labelY = ends.map((end) => y(end.value) + 4);
      if (Math.abs(labelY[0] - labelY[1]) < 14) {
        const upper = labelY[0] <= labelY[1] ? 0 : 1;
        labelY[upper] = labelY[1 - upper] - 14;
      }
      ends.forEach((end, index) => {
        let path = "";
        months.forEach((month, position) => {
          const x0 = margin.left + position * band, x1 = x0 + band;
          path += `${position ? "L" : "M"}${x0},${y(month[end.entry.id])}L${x1},${y(month[end.entry.id])}`;
        });
        const line = svg("path", { d: path, fill: "none", stroke: end.entry.colour, "stroke-width": 2, "stroke-linejoin": "round" });
        if (end.entry.dash) line.setAttribute("stroke-dasharray", end.entry.dash);
        chart.append(line);
        const label = svg("text", { class: "end-label", x: margin.left + plotW + 8, y: labelY[index] });
        label.textContent = plural(end.value, end.entry.one, end.entry.many);
        chart.append(label);
      });

      const bands = [];
      months.forEach((month, index) => {
        const hit = svg("rect", { class: "band", x: margin.left + index * band, y: margin.top, width: band, height: plotH });
        hit.addEventListener("pointermove", (event) => {
          bands.forEach((other) => other.classList.toggle("active", other === hit));
          showTooltip(event, `By the end of ${monthName(month.month)}`, series.map((entry) => ({
            colour: entry.colour, name: month[entry.id] === 1 ? entry.one : entry.many, value: number.format(month[entry.id]),
          })));
        });
        hit.addEventListener("pointerleave", () => { hit.classList.remove("active"); hideTooltip(); });
        bands.push(hit);
        chart.append(hit);
      });
      holder.replaceChildren(chart);
    }

    const table = el("table", {},
      el("thead", {}, el("tr", {}, el("th", { text: "By the end of" }), series.map((entry) => el("th", { class: "num", text: entry.name })))),
      el("tbody", {}, [...months].reverse().map((month) =>
        el("tr", {}, el("td", { text: monthName(month.month) }),
          series.map((entry) => el("td", { class: "num", text: number.format(month[entry.id]) }))))));

    const section = el("section", { id: "spread" },
      el("h2", { text: "How declaring spread" }),
      el("p", { class: "sub", text: "The projects followed here, and the people in them, with at least one commit naming a model so far. A line only goes up: it counts the first time, not what came after." }),
      el("div", { class: "card" },
        el("div", { class: "chart-head" },
          el("ul", { class: "legend" }, series.map((entry) =>
            el("li", {}, el("span", { class: "line-key", style: `border-top:2px ${entry.dash ? "dashed" : "solid"} ${entry.colour}` }), entry.name)))),
        holder,
        el("details", { class: "table-view" }, el("summary", { text: "Show as a table" }), el("div", { class: "table-scroll" }, table))));
    new ResizeObserver(draw).observe(holder);
    return section;
  }

  function perPerson(stats) {
    if (!stats.per_person.length) return null;
    const people = stats.per_person.reduce((sum, row) => sum + row.people, 0);
    const most = stats.per_person.length;
    return el("section", { id: "people" },
      el("h2", { text: "How many models a person names" }),
      el("p", { class: "sub", text: "People who named a model at least once, by the number of different models and versions they named, all projects together. Nobody is named: this shows that people change models." }),
      el("div", { class: "card" }, bars(stats.per_person.map((row) => ({
        name: (row.models === 5 && most === 5 ? "5 models or more" : plural(row.models, "model")),
        value: row.people, figureSmall: percent(row.people, people),
        title: `${plural(row.people, "person", "people")} named ${row.models === 5 && most === 5 ? "5 models or more" : plural(row.models, "model")}`,
      })))),
      stats.tool_only_people ? el("p", { class: "sub after", text: `${plural(stats.tool_only_people, "person", "people")} named only a tool whose model is not named, and ${stats.tool_only_people === 1 ? "is" : "are"} not in this chart.` }) : null);
  }

  function vendors(stats) {
    return el("section", { id: "vendors" },
      el("h2", { text: "Vendors" }),
      el("p", { class: "sub", text: "The same commits, under the vendor of the first model each one names." }),
      el("div", { class: "card" }, bars(stats.vendors.map((vendor) => ({
        name: vendor.name, value: vendor.commits,
        small: [vendor.models ? plural(vendor.models, "model") + " named" : "",
          vendor.tools ? plural(vendor.tools, "tool") + ", model not named" : ""].filter(Boolean).join(" · "),
        figureSmall: percent(vendor.commits, stats.totals.commits),
        title: `${vendor.name}: ${plural(vendor.commits, "commit")}`,
      })))));
  }

  function statsReading(stats) {
    return el("section", { id: "reading" },
      el("h2", { text: "How to read these figures" }),
      el("ul", { class: "notes" },
        el("li", { text: "These figures count what is declared: a commit “names a model” when a Co-Authored-By trailer of its message names an AI model, or when an AI agent is its author. They are a lower bound. Use that is not declared cannot be seen." }),
        stats.totals.tools ? el("li", { text: TOOL_NOTE }) : null,
        el("li", { text: `They say which models are named in the ${plural(stats.projects, "project")} followed here, not which models are the most used in general: the projects are few, and several are written by the same people.` }),
        el("li", { text: "Nothing is said here of the commits that name no model, nor of their share: the projects are of very different ages, and adding them up would mean nothing. Each project page gives its own figures." }),
        stats.totals.lines === null ? null : el("li", { text: "“Lines changed” are the lines a commit adds plus the lines it deletes, as GitHub counts them. A commit that names a model counts in full, whoever wrote each line." }),
        el("li", { text: "A person who contributes to several projects is counted once, by GitHub account, or by name when no account is known. Commits by dependency-update bots are left out." }),
        el("li", { text: "This page takes no side on the use of AI, and no side between models. It exists because the figures are interesting, not to rank anyone." })));
  }

  function renderStats(stats) {
    if (!stats.totals.commits) {
      root.replaceChildren(statsIntro(stats), el("p", { class: "empty", text: "No commit names a model yet." }));
      return;
    }
    const palette = colours(stats);
    root.replaceChildren(...[statsIntro(stats), statsTiles(stats), mostNamed(stats, palette),
      timeline(stats, palette, NAMED),
      calendar(stats.days, stats.generated_at.slice(0, 10), "Commits naming a model on each day of the last year, all projects together. A stronger blue is a day with more of them."),
      lifetimes(stats, palette), vendors(stats), spread(stats), perPerson(stats), statsReading(stats)].filter(Boolean));
    anchor();
    document.getElementById("footer").textContent =
      `Built on ${day(stats.generated_at.slice(0, 10))} from the public history of ${plural(stats.projects, "project")}.`;
  }

  async function json(path) {
    const response = await fetch(path, { cache: "no-cache" });
    if (!response.ok) throw new Error(`${path}: ${response.status}`);
    return response.json();
  }

  async function load(slug) {
    try {
      render(await json(`data/${encodeURIComponent(slug)}.json`));
    } catch (error) {
      root.replaceChildren(el("p", { class: "error", text: "The report could not be loaded. " + error.message }));
    }
  }

  // The last months of a project, as a small chart: commits, and those naming a model.
  // Each project has its own scale: the shape is shown, not the size.
  function spark(recent) {
    const count = recent.commits.length;
    const peak = Math.max(1, ...recent.commits);
    const width = 240, height = 36, band = width / count, barW = band - 2;
    const named = recent.named.reduce((sum, value) => sum + value, 0);
    const all = recent.commits.reduce((sum, value) => sum + value, 0);
    const chart = svg("svg", { viewBox: `0 0 ${width} ${height}`, preserveAspectRatio: "none", role: "img",
      "aria-label": `Last ${count} months: ${number.format(named)} of ${plural(all, "commit")} name a model.` });
    recent.commits.forEach((value, index) => {
      const x = index * band + 1;
      const full = value ? Math.max(1.5, (value / peak) * (height - 1)) : 0;
      const part = recent.named[index] ? Math.max(1.5, (recent.named[index] / peak) * (height - 1)) : 0;
      if (full) chart.append(svg("rect", { class: "all", x, y: height - full, width: barW, height: full, rx: 1 }));
      if (part) chart.append(svg("rect", { class: "named", x, y: height - part, width: barW, height: part, rx: 1 }));
    });
    chart.append(svg("line", { class: "base", x1: 0, x2: width, y1: height - 0.5, y2: height - 0.5 }));
    return el("div", { class: "spark" }, chart,
      el("div", { class: "spark-note" }, el("span", { text: day(recent.from) }),
        el("span", {}, swatch("var(--series-1)"), "naming a model"), el("span", { text: "now" })));
  }

  function overview(index) {
    document.title = "AI transparency for Open Source projects";
    root.replaceChildren(
      el("div", { class: "intro" },
        el("h1", { text: "AI transparency for Open Source projects" }),
        el("p", { text: "What the contributors of each project declare about their use of AI tools, read from the Co-Authored-By trailers of its commits and from its pull requests." })),
      el("div", { class: "projects" }, index.map((project) => {
        const totals = project.totals;
        const since = project.trailer_since;
        const part = since ? totals.since_ai_commits : totals.ai_commits;
        const whole = since ? totals.since_commits : totals.human_commits;
        return el("a", { class: "project-card", href: "?project=" + encodeURIComponent(project.slug) },
          el("h2", { text: project.name }),
          el("div", { class: "repo", text: project.repository }),
          el("div", { class: "value", text: percent(part, whole) }),
          el("div", { class: "label", text: `of commits declare an AI model${since ? " since " + day(since) : ""} (${number.format(part)} of ${number.format(whole)})` }),
          el("div", { class: "meter", role: "presentation" }, el("span", { style: `width:${whole ? (100 * part) / whole : 0}%` })),
          project.recent ? spark(project.recent) : null,
          el("p", { class: "facts", text: `${plural(totals.humans, "contributor")}, ${number.format(totals.humans_with_ai)} declared a model · ${plural(totals.models, "model")} named` }));
      })));
    document.getElementById("footer").textContent = "Built from the public history of each project.";
  }

  async function start() {
    if (root.dataset.page === "stats") {
      try {
        renderStats(await json("data/stats.json"));
      } catch (error) {
        root.replaceChildren(el("p", { class: "error", text: "The statistics could not be loaded. " + error.message }));
      }
      return;
    }
    let index;
    try {
      index = await json("data/index.json");
    } catch (error) {
      root.replaceChildren(el("p", { class: "error", text: "No report has been built yet. " + error.message }));
      return;
    }
    const wanted = new URLSearchParams(location.search).get("project");
    const found = index.find((project) => project.slug === wanted);
    const current = found || (index.length === 1 ? index[0] : null);
    if (index.length > 1) {
      const select = document.getElementById("project-select");
      select.replaceChildren(
        el("option", { value: "", selected: !current, text: "All projects" }),
        ...index.map((project) =>
          el("option", { value: project.slug, selected: current && project.slug === current.slug, text: project.name })));
      select.addEventListener("change", () => {
        location.href = select.value ? "?project=" + encodeURIComponent(select.value) : "./";
      });
      select.closest("label").hidden = false;
    }
    if (current) load(current.slug);
    else {
      document.querySelector('.nav a[href="./"]').setAttribute("aria-current", "page");
      overview(index);
    }
  }

  window.addEventListener("scroll", hideTooltip, { passive: true });
  start();
})();
