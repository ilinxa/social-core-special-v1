// Quick debug script to understand the grouping behavior

function toDateKey(dateStr) {
  const d = new Date(dateStr);
  return `${d.getFullYear()}-${d.getMonth()}-${d.getDate()}`;
}

function isWithinGap(a, b) {
  const GROUP_GAP_MS = 5 * 60 * 1000;
  return Math.abs(new Date(b).getTime() - new Date(a).getTime()) <= GROUP_GAP_MS;
}

const msg1 = {
  id: "msg-1",
  sender_id: "user-1",
  sender_type: "user",
  created_at: "2024-03-20T23:55:00Z",
};

const msg2 = {
  id: "msg-2",
  sender_id: "user-1",
  sender_type: "user",
  created_at: "2024-03-21T00:05:00Z",
};

console.log("Message 1 date key:", toDateKey(msg1.created_at));
console.log("Message 2 date key:", toDateKey(msg2.created_at));
console.log("Are they the same day?", toDateKey(msg1.created_at) === toDateKey(msg2.created_at));
console.log("Are they within 5 min gap?", isWithinGap(msg1.created_at, msg2.created_at));
console.log("");
console.log("In local timezone:");
console.log("Message 1:", new Date(msg1.created_at).toString());
console.log("Message 2:", new Date(msg2.created_at).toString());
