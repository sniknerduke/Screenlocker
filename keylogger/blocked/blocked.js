// Get the original URL from query params
const params = new URLSearchParams(window.location.search);
const originalUrl = params.get("url");

// Display blocked URL
const urlDisplay = document.getElementById("blocked-url");
if (originalUrl) {
  try {
    const hostname = new URL(originalUrl).hostname;
    urlDisplay.textContent = hostname;
  } catch {
    urlDisplay.textContent = originalUrl;
  }
}

const passwordInput = document.getElementById("password-input");
const btnUnlock = document.getElementById("btn-unlock");
const errorMsg = document.getElementById("error-msg");

function showError(msg) {
  errorMsg.textContent = msg;
  setTimeout(() => {
    errorMsg.textContent = "";
  }, 3000);
}

async function tryUnlock() {
  const password = passwordInput.value;
  if (!password) {
    return showError("Vui lòng nhập mật khẩu!");
  }

  btnUnlock.textContent = "Đang xác thực...";
  btnUnlock.disabled = true;

  try {
    const response = await chrome.runtime.sendMessage({
      type: "VERIFY_PASSWORD",
      password: password,
      url: originalUrl,
    });

    if (response.success) {
      // Redirect to the original URL
      window.location.href = originalUrl;
    } else {
      showError("Sai mật khẩu! Thử lại.");
      passwordInput.value = "";
      passwordInput.focus();
    }
  } catch (err) {
    showError("Có lỗi xảy ra, thử lại.");
  }

  btnUnlock.textContent = "Mở khóa";
  btnUnlock.disabled = false;
}

btnUnlock.addEventListener("click", tryUnlock);

passwordInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") tryUnlock();
});
