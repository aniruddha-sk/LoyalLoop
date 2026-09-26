
(() => {
    let controller = null;
    let requestNumber = 0;
    let customTimer = null;

    async function updatePeriod(period, fromDate = "", toDate = "") {
        if (period === "custom" && (!fromDate || !toDate)) return;
        if (period === "custom" && fromDate > toDate) return;

        const url = new URL(window.location.href);
        url.searchParams.set("period", period);

        if (period === "custom") {
            url.searchParams.set("from_date", fromDate);
            url.searchParams.set("to_date", toDate);
        } else {
            url.searchParams.delete("from_date");
            url.searchParams.delete("to_date");
        }

        if (controller) controller.abort();
        controller = new AbortController();
        const currentRequest = ++requestNumber;

        const filter = document.querySelector(".ll-date-filter");
        const loading = document.getElementById("llFilterLoading");
        if (filter) filter.classList.add("is-loading");
        if (loading) loading.hidden = false;

        try {
            const response = await fetch(url.toString(), {
                signal: controller.signal,
                headers: { "X-Requested-With": "XMLHttpRequest" },
                credentials: "same-origin"
            });

            if (!response.ok) throw new Error("Unable to load data");

            const html = await response.text();
            if (currentRequest !== requestNumber) return;

            const doc = new DOMParser().parseFromString(html, "text/html");
            const nextContent = doc.querySelector(".dashboard-content");
            const currentContent = document.querySelector(".dashboard-content");

            if (!nextContent || !currentContent) {
                window.location.href = url.toString();
                return;
            }

            currentContent.replaceWith(nextContent);
            history.pushState({}, "", url.toString());
            bindFilter();
        } catch (error) {
            if (error.name === "AbortError") return;
            console.error("Date filter error:", error);
            const currentLoading = document.getElementById("llFilterLoading");
            if (currentLoading) {
                currentLoading.textContent = "Unable to update. Please try again.";
                currentLoading.hidden = false;
            }
        } finally {
            if (currentRequest === requestNumber) {
                const currentFilter = document.querySelector(".ll-date-filter");
                const currentLoading = document.getElementById("llFilterLoading");
                if (currentFilter) currentFilter.classList.remove("is-loading");
                if (currentLoading && currentLoading.textContent === "Updating…") {
                    currentLoading.hidden = true;
                }
            }
        }
    }

    function bindFilter() {
        const period = document.getElementById("llPeriod");
        const year = document.getElementById("llYear");
        const month = document.getElementById("llMonth");
        const from = document.getElementById("llFrom");
        const to = document.getElementById("llTo");
        const custom = document.getElementById("llCustomRange");

        if (!period || !year || !month || !from || !to) return;

        period.addEventListener("change", () => {
            if (period.value === "custom") {
                custom.classList.add("is-visible");
                if (!from.value) from.value = new Date().toLocaleDateString("en-CA");
                if (!to.value) to.value = new Date().toLocaleDateString("en-CA");
                updatePeriod("custom", from.value, to.value);
            } else {
                custom.classList.remove("is-visible");
                updatePeriod(period.value);
            }
        });

        year.addEventListener("change", () => {
            if (!year.value) return;
            updatePeriod(month.value
                ? `month:${year.value}-${month.value}`
                : `year:${year.value}`);
        });

        month.addEventListener("change", () => {
            if (!month.value) {
                if (year.value) updatePeriod(`year:${year.value}`);
                return;
            }
            const selectedYear = year.value || new Date().getFullYear();
            updatePeriod(`month:${selectedYear}-${month.value}`);
        });

        const onCustomChange = () => {
            clearTimeout(customTimer);
            customTimer = setTimeout(() => {
                if (from.value && to.value && from.value <= to.value) {
                    updatePeriod("custom", from.value, to.value);
                }
            }, 250);
        };

        from.addEventListener("change", onCustomChange);
        to.addEventListener("change", onCustomChange);
    }

    window.addEventListener("popstate", () => {
        window.location.reload();
    });

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", bindFilter);
    } else {
        bindFilter();
    }
})();
