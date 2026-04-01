// ===== Utility =====
async function hashPassword(password) {
  const encoder = new TextEncoder();
  const data = encoder.encode(password);
  const hashBuffer = await crypto.subtle.digest("SHA-256", data);
  const hashArray = Array.from(new Uint8Array(hashBuffer));
  return hashArray.map((b) => b.toString(16).padStart(2, "0")).join("");
}

function showStatus(msg, type = "error") {
  const el = document.getElementById("status-msg");
  el.textContent = msg;
  el.className = `status ${type}`;
  setTimeout(() => {
    el.textContent = "";
    el.className = "status";
  }, 3000);
}

function showSection(id) {
  document
    .querySelectorAll(
      "#setup-section, #login-section, #main-section, #change-pass-section"
    )
    .forEach((s) => s.classList.add("hidden"));
  document.getElementById(id).classList.remove("hidden");
}

// ===== Storage helpers =====
function getData() {
  return new Promise((resolve) => {
    chrome.storage.local.get(["passwordHash", "blockedSites"], (result) => {
      resolve({
        passwordHash: result.passwordHash || null,
        blockedSites: result.blockedSites || [],
      });
    });
  });
}

function saveData(data) {
  return new Promise((resolve) => {
    chrome.storage.local.set(data, resolve);
  });
}

// ===== Render site list =====
function renderSites(sites) {
  const list = document.getElementById("site-list");
  if (sites.length === 0) {
    list.innerHTML =
      '<p style="text-align:center;color:#666;font-size:12px;padding:12px 0;">Chưa có website nào được khóa</p>';
    return;
  }
  list.innerHTML = sites
    .map(
      (site, i) => `
    <div class="site-item">
      <span>🔒 ${site}</span>
      <button class="remove-btn" data-index="${i}" title="Xóa">✕</button>
    </div>
  `
    )
    .join("");

  list.querySelectorAll(".remove-btn").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const idx = parseInt(btn.dataset.index);
      const data = await getData();
      data.blockedSites.splice(idx, 1);
      await saveData({ blockedSites: data.blockedSites });
      renderSites(data.blockedSites);
      showStatus("Đã xóa!", "success");
    });
  });
}

// ===== Normalize domain =====
function normalizeDomain(input) {
  let domain = input.trim().toLowerCase();
  domain = domain.replace(/^(https?:\/\/)/, "");
  domain = domain.replace(/\/.*$/, "");
  domain = domain.replace(/^www\./, "");
  return domain;
}

// ===== Init =====
document.addEventListener("DOMContentLoaded", async () => {
  const data = await getData();

  if (!data.passwordHash) {
    showSection("setup-section");
  } else {
    showSection("login-section");
  }

  // Setup password
  document.getElementById("btn-setup").addEventListener("click", async () => {
    const pass = document.getElementById("setup-password").value;
    const confirm = document.getElementById("setup-confirm").value;

    if (pass.length < 4) {
      return showStatus("Mật khẩu tối thiểu 4 ký tự!");
    }
    if (pass !== confirm) {
      return showStatus("Mật khẩu xác nhận không khớp!");
    }

    const hash = await hashPassword(pass);
    await saveData({ passwordHash: hash });
    showStatus("Tạo mật khẩu thành công!", "success");

    const freshData = await getData();
    renderSites(freshData.blockedSites);
    showSection("main-section");
  });

  // Login
  document.getElementById("btn-login").addEventListener("click", async () => {
    const pass = document.getElementById("login-password").value;
    const hash = await hashPassword(pass);
    const stored = await getData();

    if (hash !== stored.passwordHash) {
      return showStatus("Sai mật khẩu!");
    }

    renderSites(stored.blockedSites);
    showSection("main-section");
    showStatus("Mở khóa thành công!", "success");
  });

  // Enter key for login
  document
    .getElementById("login-password")
    .addEventListener("keydown", (e) => {
      if (e.key === "Enter") document.getElementById("btn-login").click();
    });

  // Add site
  document.getElementById("btn-add").addEventListener("click", async () => {
    const input = document.getElementById("site-input");
    const domain = normalizeDomain(input.value);

    if (!domain || !domain.includes(".")) {
      return showStatus("Vui lòng nhập tên miền hợp lệ!");
    }

    const data = await getData();
    if (data.blockedSites.includes(domain)) {
      return showStatus("Website này đã có trong danh sách!");
    }

    data.blockedSites.push(domain);
    await saveData({ blockedSites: data.blockedSites });
    input.value = "";
    renderSites(data.blockedSites);
    showStatus(`Đã khóa ${domain}!`, "success");
  });

  // Enter key for add site
  document.getElementById("site-input").addEventListener("keydown", (e) => {
    if (e.key === "Enter") document.getElementById("btn-add").click();
  });

  // Lock
  document.getElementById("btn-lock").addEventListener("click", () => {
    showSection("login-section");
    document.getElementById("login-password").value = "";
  });

  // Change password
  document
    .getElementById("btn-change-pass")
    .addEventListener("click", () => {
      showSection("change-pass-section");
    });

  document
    .getElementById("btn-cancel-change")
    .addEventListener("click", async () => {
      const data = await getData();
      renderSites(data.blockedSites);
      showSection("main-section");
    });

  document
    .getElementById("btn-save-pass")
    .addEventListener("click", async () => {
      const oldPass = document.getElementById("old-password").value;
      const newPass = document.getElementById("new-password").value;
      const newConfirm = document.getElementById("new-confirm").value;

      const data = await getData();
      const oldHash = await hashPassword(oldPass);

      if (oldHash !== data.passwordHash) {
        return showStatus("Mật khẩu cũ không đúng!");
      }
      if (newPass.length < 4) {
        return showStatus("Mật khẩu mới tối thiểu 4 ký tự!");
      }
      if (newPass !== newConfirm) {
        return showStatus("Xác nhận mật khẩu không khớp!");
      }

      const newHash = await hashPassword(newPass);
      await saveData({ passwordHash: newHash });

      document.getElementById("old-password").value = "";
      document.getElementById("new-password").value = "";
      document.getElementById("new-confirm").value = "";

      renderSites(data.blockedSites);
      showSection("main-section");
      showStatus("Đổi mật khẩu thành công!", "success");
    });
});
