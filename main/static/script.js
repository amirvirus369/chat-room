// مدیریت باز و بسته کردن مودال جستجو
const searchModal = document.getElementById('searchModal');
const searchIcon = document.getElementById('search'); // آیکون جستجو در هدر چت
const closeSearchBtn = document.getElementById('closeSearchModal');
const liveSearchInput = document.getElementById('liveSearchInput');
const searchResults = document.getElementById('searchResults');

// باز کردن مودال با کلیک روی آیکون جستجو
if (searchIcon) {
    searchIcon.addEventListener('click', () => {
        searchModal.style.display = 'flex';
        if (liveSearchInput) liveSearchInput.focus();
    });
}

// بستن مودال با کلیک روی دکمه ضربدر
if (closeSearchBtn) {
    closeSearchBtn.addEventListener('click', () => {
        searchModal.style.display = 'none';
        searchResults.innerHTML = '';
        if (liveSearchInput) liveSearchInput.value = '';
    });
}

// بستن مودال با کلیک روی پس‌زمینه تاریک بیرون از باکس
window.addEventListener('click', (e) => {
    if (e.target === searchModal) {
        searchModal.style.display = 'none';
        searchResults.innerHTML = '';
        if (liveSearchInput) liveSearchInput.value = '';
    }
});


const chatList = document.querySelector('.chat-list');

function findChatItem(name) {
    return Array.from(chatList.querySelectorAll('.chat-item'))
        .find(el => el.dataset.name === name);
}
const norm = s => (s || '').trim().replace(/ي/g, 'ی').replace(/ك/g, 'ک');

function createChatItem(name) {
    const item = document.createElement('div');
    item.className = 'chat-item';
    item.dataset.name = name;
    item.innerHTML = `
        <div class="avatar" style="background: linear-gradient(135deg, #3b82f6, #1d4ed8);"></div>
        <div class="chat-info">
            <div class="chat-name-time">
                <span class="chat-name"></span>
                <span class="chat-time"></span>
            </div>
            <div class="chat-last-msg"></div>
        </div>
        <span class="unread-badge unread" style="display:none;">0</span>
        <span class="unread-badge online-badge" style="display:flex;">انلاین</span>`;

    item.querySelector('.chat-name').textContent = name;
    item.querySelector('.chat-last-msg').id = `last-message-${name}`;
    item.querySelector('.unread').id = `unread-${name}`;
    item.querySelector('.online-badge').id = `un-${name}`;

    item.addEventListener('click', () => {
        window.location.href = `/chat/${encodeURIComponent(name)}/`;
    });
    return item;
}

function updateSidebar(name, message, time, isIncoming) {
    let item = findChatItem(name);
    if (!item) item = createChatItem(name);       

    item.querySelector('.chat-last-msg').textContent = message;
    item.querySelector('.chat-time').textContent = time;

    const badge = item.querySelector('.unread-badge[id^="unread-"]');
    const inThisChat = norm(name) === norm(User);

    if (badge) {
        if (isIncoming && !inThisChat) {           
            let count = parseInt(badge.textContent, 10);
            if (isNaN(count)) count = 0;            
            badge.textContent = count + 1;
            badge.style.display = 'flex';
        } else if (inThisChat) {                   
            badge.textContent = 0;
            badge.style.display = 'none';
        }
    }

    if (chatList.firstElementChild !== item) chatList.prepend(item);   
}

const msgInput = document.getElementById("messageInput");
const sendBtn = document.getElementById("btn");
const msgArea = document.getElementById("messagesContainer");


const StatusUser = document.getElementById('userStatus')
const User = '{{username.full_name}}'
const me = '{{request.user.full_name}}'
function CheckUser(status){
    if (!StatusUser) return;
    if (status == 'online'){
        StatusUser.textContent = 'انلاین';
        StatusUser.className = 'online';
        StatusUser.style = 'color:green';
    }else{
        StatusUser.textContent = 'افلاین';
        StatusUser.className = 'offline';
        StatusUser.style = 'color:red';
    }
}
const address = window.location.protocol === 'https:' ? 'wss' : 'ws'
const web = new WebSocket(`${address}://${window.location.host}/websocket/${User}`)

function getCurrentTime() {
    return new Date().toLocaleTimeString("fa-IR", { hour: "2-digit", minute: "2-digit" });
}

function scrollToBottom() {
    if (msgArea) {
        msgArea.scrollTop = msgArea.scrollHeight;
    }
}
function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
}

function SendMessage(){
    const Message = msgInput.value.trim()
   if (!Message || web.readyState !== WebSocket.OPEN) {
  console.log('WebSocket is not open');
  return;
}
    
    web.send(JSON.stringify({msg:Message,type:'new'}))
    const time = getCurrentTime()
    msgArea.insertAdjacentHTML(
        'beforeend',
        ` <div class="message outgoing">
                   ${escapeHtml(Message)}
                    <div class="message-footer">
                        <span class="time">${time}</span>
                        <span class="message-status sent tik-status">
                            <i class="fa-solid fa-check"></i>
                            <i class="fa-solid fa-check"></i>
                        </span>
                    </div>
                </div>`
    )
    
    msgInput.value = ''
    scrollToBottom()
    updateSidebar(User, Message, new Date().toLocaleTimeString('en-GB', {hour: '2-digit', minute: '2-digit'}), false);

}

if (sendBtn) sendBtn.addEventListener("click", SendMessage);
if (msgInput) {
    msgInput.addEventListener("keydown", function (event) {
        if (event.key === "Enter") {
            event.preventDefault();
            SendMessage();
        }
    });
}



web.onopen = function(){
    console.log('connect done ')
    const statusme = document.getElementById('statusme')
    if(statusme){
        statusme.textContent = 'انلاین'
        statusme.style.color = 'green'
    }
    web.send(JSON.stringify({type:'ihave_seen'}))

    const TotalNotif = document.getElementById(`unread-${User}`)
    if (TotalNotif){
        TotalNotif.textContent = 0
        TotalNotif.style.display = 'none'
    }
}
if(liveSearchInput){
    liveSearchInput.addEventListener('input',function(){
        const query = this.value.trim()
        if(query.length === 0){
            searchResults.innerHTML = ''
            return
        }
        if(web.readyState === WebSocket.OPEN){
            web.send(JSON.stringify({
                'quary':query,
                'type':'search'
            }))
        }
    })
}
web.onmessage = function(event){
    let data;
    try{
        data = JSON.parse(event.data)
    }catch(e){
        return
    }
    if (data.type_of_data === 'onlainam'){
        if (data.user_name === User){
            CheckUser(data.status)
            console.log('همین صفحه')
            const TotalNotif = document.getElementById(`un-${data.user_name}`)
            TotalNotif.textContent = 'انلاین'
            TotalNotif.style.color = 'green'
            
        }
        else{
            const TotalNotif = document.getElementById(`un-${data.user_name}`)
            TotalNotif.textContent = 'انلاین'
            TotalNotif.style.color = 'green'
            console.log('صفحه ی دیگه')
        }

    }

    if (data.type_of_data === 'new'){
         updateSidebar(data.sender, data.message, data.date, true);
         
    const senderStatusBadge = document.getElementById(`un-${data.sender}`);
         if (senderStatusBadge) {
             senderStatusBadge.textContent = 'انلاین';
             senderStatusBadge.style.color = 'green';
         }
    
        if(data.sender === User){
            console.log('در همین صفحه بود ')
             msgArea.insertAdjacentHTML(
        'beforeend',
        ` <div class="message incoming">
                   ${data.message}
                    <div class="message-footer">
                        <span class="time">${data.date}</span>
                    </div>
                </div>`

    )
    scrollToBottom()
    if (web.readyState === WebSocket.OPEN){
        web.send(JSON.stringify({type:'ihave_seen'}))
    }
        }
    
    }
    if (data.type_of_data === 'ihave_seen' || data.type === 'send_send'){
        console.log('اره اوومد ')
        if (me === data.sender || data.sender === User){
            const all_chat = document.querySelectorAll('.message.outgoing .message-status.sent')
            all_chat.forEach(function (e){
                e.classList.remove('sent')
                e.classList.add('read')
            })
        }

    }
    if (data.type_of_data === 'search'){
        console.log('سرچ اومد')
        searchResults.innerHTML = ''
        if (data.users.length === 0 ){
            searchResults.innerHTML = '<p style="color:gray; text-align:center;">کاربری یافت نشد</p>';
            return;
        }
        data.users.forEach(user =>{
            const item = document.createElement('div');
            item.style.padding = '8px 12px';
            item.style.cursor = 'pointer';
            item.style.borderBottom = '1px solid #eee';
            item.textContent = user.full_name;
            item.addEventListener('click',()=>{
                window.location.href = `/chat/${encodeURIComponent(user.full_name)}`
            } )
            searchResults.appendChild(item)
        })
    }
}
web.onclose = function(){
    const TotalNotif = document.getElementById('statusme')
            TotalNotif.textContent = 'افلاین (دوباره تلاش کنید)'
            TotalNotif.style.color = 'red'

}

web.onerror = function(){
const TotalNotif = document.getElementById('statusme')
            TotalNotif.textContent = 'افلاین (دوباره تلاش کنید)'
            TotalNotif.style.color = 'red'
}
// مدیریت نمایش منوی همبرگری
const hamburgerBtn = document.getElementById("hamburgerBtn");
const hamburgerMenu = document.getElementById("hamburgerMenu");

hamburgerBtn.addEventListener("click", function (e) {
    e.stopPropagation();
    hamburgerMenu.classList.toggle("show");
    threeDotsMenu.classList.remove("show"); // بستن منوی دیگر
});

// مدیریت نمایش منوی سه نقطه چت (مسدود کردن)
const threeDotsBtn = document.getElementById("threeDotsBtn");
const threeDotsMenu = document.getElementById("threeDotsMenu");

threeDotsBtn.addEventListener("click", function (e) {
    e.stopPropagation();
    threeDotsMenu.classList.toggle("show");
    hamburgerMenu.classList.remove("show"); // بستن منوی دیگر
});

// بستن منوها با کلیک در خارج از آن‌ها
window.addEventListener("click", function () {
    hamburgerMenu.classList.remove("show");
    threeDotsMenu.classList.remove("show");
});

// مدیریت نمایش سایدبار و صفحه چت در موبایل (ریپانسیو)
const appContainer = document.querySelector(".app-container");
const backBtn = document.querySelector(".back-btn");

function isMobileLayout() {
    return window.matchMedia("(max-width: 768px)").matches;
}

function openMobileChat() {
    if (isMobileLayout() && appContainer) {
        appContainer.classList.add("mobile-chat-open");
    }
}

function closeMobileChat() {
    if (appContainer) {
        appContainer.classList.remove("mobile-chat-open");
    }
}

if (backBtn) {
    backBtn.addEventListener("click", closeMobileChat);
}

document.querySelectorAll(".chat-item").forEach(function (item) {
    item.addEventListener("click", function () {
        openMobileChat();
    });
});

if (isMobileLayout() && appContainer) {
    appContainer.classList.add("mobile-chat-open");
}

window.addEventListener("resize", function () {
    if (!isMobileLayout() && appContainer) {
        appContainer.classList.remove("mobile-chat-open");
    }
});



function setMyStatus(state) {
    const map = {
        connecting:   ['در حال اتصال...', 'orange'],
        connected:    ['متصل', 'green'],
        disconnected: ['قطع شده', 'red'],
    };
    const [text, color] = map[state];
    if (myStatus) { myStatus.textContent = text; myStatus.style.color = color; }
    if (myDot) myDot.style.background = color;
}




scrollToBottom();