// Content shown on the page, kept separate from the layout so it is easy to edit.
import {
  Brain,
  CreditCard,
  GitBranch,
  Landmark,
  MessageCircleQuestion,
  Receipt,
  Reply,
  Search,
  ShieldAlert,
  Siren,
} from "lucide-react";

export const MAX_LENGTH = 2000;

export const EXAMPLES = [
  {
    title: "Charged twice",
    icon: Receipt,
    text: "I was charged twice for the same transaction and I need this resolved immediately. If not, I will escalate.",
  },
  {
    title: "Stolen card",
    icon: Siren,
    text: "Someone stole my wallet this morning and my debit card was inside. Please block it right now!",
  },
  {
    title: "Phishing text",
    icon: ShieldAlert,
    text: "I got a text saying my account is locked. I clicked the link and typed in my card number. Did I just get scammed?",
  },
  {
    title: "Loan question",
    icon: Landmark,
    text: "Hi, is there a fee if I pay back my personal loan early?",
  },
  {
    title: "Card declined",
    icon: CreditCard,
    text: "My card keeps getting declined at the supermarket but I definitely have money in my account.",
  },
  {
    title: "Vague message",
    icon: MessageCircleQuestion,
    text: "it stopped working again",
  },
];

export const STEPS = [
  { title: "Understand", detail: "Intents, priority and entities", icon: Brain },
  { title: "Decide", detail: "Team and next action", icon: GitBranch },
  { title: "Retrieve", detail: "Relevant bank policies", icon: Search },
  { title: "Respond", detail: "Reply grounded in policy", icon: Reply },
];

export const HOW_IT_WORKS = [
  {
    title: "Understand",
    icon: Brain,
    text: "A language model reads the message and extracts intents, issue type, priority and entities. Its output must match a strict JSON schema, so it is always complete and valid.",
  },
  {
    title: "Decide",
    icon: GitBranch,
    text: "Deterministic rules, not the model, choose the team and the next action. Fraud is always escalated, even when the customer writes calmly.",
  },
  {
    title: "Retrieve",
    icon: Search,
    text: "The message is compared by meaning with 71 passages from 12 policy documents, and the closest ones are passed to the model (retrieval-augmented generation).",
  },
  {
    title: "Respond",
    icon: Reply,
    text: "The model drafts a short reply using only the retrieved policy text and cites each source, so an agent can check every claim before sending.",
  },
];

export const METRICS = [
  { value: "96.7%", label: "Routing accuracy" },
  { value: "91.7%", label: "Next-action accuracy" },
  { value: "0", label: "Replies with invented numbers" },
  { value: "100%", label: "Same input, same output" },
];

export const GITHUB_URL = "https://github.com/ghostm1lk/task3_project";
