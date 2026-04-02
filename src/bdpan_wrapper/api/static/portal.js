const output = document.getElementById("response-output");

function setOutput(value) {
  output.textContent = typeof value === "string" ? value : JSON.stringify(value, null, 2);
}

async function requestJson(url, options = {}) {
  const response = await fetch(url, options);
  const text = await response.text();
  try {
    return JSON.parse(text);
  } catch {
    return { status: response.status, raw: text };
  }
}

async function loadRuntimeStatus() {
  const container = document.getElementById("runtime-status");
  container.textContent = "Loading...";
  const data = await requestJson("/api/v1/system/status");
  if (data.success) {
    const payload = data.data;
    container.innerHTML = `
      <strong>${payload.bdpan_available ? "Runtime available" : "Runtime unavailable"}</strong>
      <div>bdpan: ${payload.bdpan_bin}</div>
      <div>runtime: ${payload.runtime_home}</div>
      <div>uploads: ${payload.uploads_dir}</div>
    `;
  } else {
    container.textContent = data.message || "Failed to load runtime status";
  }
}

function bindTabs() {
  const tabs = document.querySelectorAll(".tester-tabs button");
  const groups = document.querySelectorAll(".tester-group");
  tabs.forEach((button) => {
    button.addEventListener("click", () => {
      tabs.forEach((item) => item.classList.remove("active"));
      groups.forEach((item) => item.classList.remove("active"));
      button.classList.add("active");
      document.getElementById(button.dataset.target)?.classList.add("active");
    });
  });
}

async function sendRest() {
  const endpoint = document.getElementById("rest-endpoint").value;
  const bodyText = document.getElementById("rest-body").value.trim();
  const isGet =
    endpoint.startsWith("/api/v1/accounts") ||
    endpoint.startsWith("/api/v1/tasks") ||
    endpoint.startsWith("/api/v1/system");
  const options = isGet
    ? {}
    : {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: bodyText ? bodyText : "{}",
      };

  try {
    setOutput("Request in progress...");
    const data = await requestJson(endpoint, options);
    setOutput(data);
  } catch (error) {
    setOutput({ error: String(error) });
  }
}

async function sendUpload() {
  const accountId = document.getElementById("upload-account-id").value.trim();
  const remotePath = document.getElementById("upload-remote-path").value.trim();
  const fileInput = document.getElementById("upload-file");
  const file = fileInput.files?.[0];

  if (!accountId || !remotePath || !file) {
    setOutput({ error: "account_id, remote_path, and file are required." });
    return;
  }

  const formData = new FormData();
  formData.append("account_id", accountId);
  formData.append("remote_path", remotePath);
  formData.append("file", file);

  try {
    setOutput("Request in progress...");
    const data = await requestJson("/api/v1/files/browser-upload-share", {
      method: "POST",
      body: formData,
    });
    setOutput(data);
  } catch (error) {
    setOutput({ error: String(error) });
  }
}

async function sendCompat() {
  const params = new URLSearchParams({
    account_id: document.getElementById("compat-account-id").value.trim(),
    url: document.getElementById("compat-url").value.trim(),
    pwd: document.getElementById("compat-pwd").value.trim(),
    path: document.getElementById("compat-path").value.trim(),
  });

  try {
    setOutput("Request in progress...");
    const data = await requestJson(`/compat/baidu/transfer?${params.toString()}`);
    setOutput(data);
  } catch (error) {
    setOutput({ error: String(error) });
  }
}

async function copyResponse() {
  try {
    await navigator.clipboard.writeText(output.textContent || "");
  } catch (error) {
    setOutput({ error: `Copy failed: ${String(error)}` });
  }
}

document.getElementById("refresh-status").addEventListener("click", loadRuntimeStatus);
document.getElementById("send-rest").addEventListener("click", sendRest);
document.getElementById("send-upload").addEventListener("click", sendUpload);
document.getElementById("send-compat").addEventListener("click", sendCompat);
document.getElementById("copy-response").addEventListener("click", copyResponse);

bindTabs();
loadRuntimeStatus();
