// ==UserScript==
// @name         Chub Prompt Toolkit
// @namespace    http://tampermonkey.net/
// @version      2026.10.08.1
// @description  Modular prompt presets, live mutations, JSON import/export, and quick insertion for chub.ai
// @author       CCI ChubChatInject
// @match        https://chub.ai/*
// @grant        none
// @run-at       document-idle
// ==/UserScript==

(function () {
  'use strict';

  const STORAGE_KEY = 'chub_prompt_toolkit_state_v1';
  const PANEL_ID = 'chub-prompt-toolkit-panel';

  const defaultState = {
    presets: [
      {
        id: 'core-roleplay',
        name: 'Core Roleplay Pack',
        description: 'General-purpose character framing and behavior clues.',
        modules: [
          {
            id: 'persona-basics',
            category: 'preprompt',
            enabled: true,
            name: 'Persona Basics',
            content: 'You are a vivid, emotionally grounded roleplay assistant. Stay in character, be consistent, and respond with a clear tone, actionable choices, and immersive detail.'
          },
          {
            id: 'impersonation',
            category: 'impersonation',
            enabled: true,
            name: 'Impersonation',
            content: 'Speak as the chosen character. Preserve their voice, motivations, and boundaries. Never break character unless the user explicitly asks for meta commentary.'
          },
          {
            id: 'scene-state',
            category: 'scene',
            enabled: true,
            name: 'Scene State',
            content: 'Current scene: cinematic, intimate, and high-stakes. Keep the environment vivid, but avoid overloading the user with irrelevant lore.'
          },
          {
            id: 'commands',
            category: 'commands',
            enabled: true,
            name: 'Command Layer',
            content: 'Command priorities: 1) stay in story, 2) honor user intent, 3) keep actions concise, 4) escalate only when needed.'
          }
        ]
      },
      {
        id: 'status-system',
        name: 'Level + Corruption System',
        description: 'Add level, status, and corruption gauges for structured scenes.',
        modules: [
          {
            id: 'status-setup',
            category: 'system',
            enabled: true,
            name: 'Status Setup',
            content: 'Character status: Level 24, Focus 72%, Resolve 80%, stamina 66%. The world state is active and dynamic; maintain continuity between scenes.'
          },
          {
            id: 'corruption-meter',
            category: 'system',
            enabled: true,
            name: 'Corruption Meter',
            content: 'Corruption meter: 32 / 100. Small changes in tone, behavior, and decision framing should reflect a gradual shift in temptation and risk.'
          },
          {
            id: 'scene-rules',
            category: 'rules',
            enabled: true,
            name: 'Scene Rules',
            content: 'If the scene becomes destabilized, maintain agency, clarity, and emotional stakes. Avoid random resets of the settings unless the user requests a fresh start.'
          }
        ]
      },
      {
        id: 'perplexity-research',
        name: 'Perplexity Research Connector',
        description: 'Research-first prompt bundle for merged data sources and offloaded synthesis.',
        modules: [
          {
            id: 'research-task',
            category: 'research',
            enabled: true,
            name: 'Research Task',
            content: 'Research goal: gather relevant external context, compare credible sources, and synthesize them into a usable answer without inventing facts.'
          },
          {
            id: 'connector-stack',
            category: 'connectors',
            enabled: true,
            name: 'Connector Stack',
            content: 'Preferred connectors: GitHub repo context, Notion knowledge base, Context7 reference material, Perplexity research summaries, local notes and prompt packs.'
          },
          {
            id: 'command-offload',
            category: 'commands',
            enabled: true,
            name: 'Command Offload',
            content: 'Workflow: gather source inputs -> summarize relevant facts -> compare conflicting details -> create final structured response -> export reusable prompt or lore block.'
          },
          {
            id: 'output-format',
            category: 'output',
            enabled: true,
            name: 'Output Format',
            content: 'Deliver the result in three sections: 1) answer, 2) citations/source summary, 3) reusable prompt pack or lorebook update.'
          }
        ]
      }
    ],
    activePresetId: 'core-roleplay',
    quickInsert: true
  };

  function deepClone(value) {
    return JSON.parse(JSON.stringify(value));
  }

  function readState() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(defaultState));
        return deepClone(defaultState);
      }
      const parsed = JSON.parse(raw);
      if (!parsed || !Array.isArray(parsed.presets)) {
        throw new Error('Missing presets');
      }
      return parsed;
    } catch (error) {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(defaultState));
      return deepClone(defaultState);
    }
  }

  function writeState(nextState) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(nextState));
  }

  function getActivePreset(state) {
    const preset = state.presets.find((item) => item.id === state.activePresetId);
    return preset || state.presets[0];
  }

  function getTextInputTarget() {
    const selectors = [
      'textarea',
      '[role="textbox"]',
      '[contenteditable="true"]',
      '[contenteditable="plaintext-only"]',
      'textarea[placeholder*="message"]',
      'textarea[placeholder*="chat"]',
      'textarea[placeholder*="prompt"]'
    ];

    for (const selector of selectors) {
      const found = document.querySelector(selector);
      if (found && isVisible(found)) {
        return found;
      }
    }

    return null;
  }

  function isVisible(element) {
    if (!element) return false;
    const style = window.getComputedStyle(element);
    if (style.display === 'none' || style.visibility === 'hidden') {
      return false;
    }
    const rect = element.getBoundingClientRect();
    return rect.width > 0 || rect.height > 0;
  }

  function setTextAtTarget(target, text) {
    if (!target) return false;

    if (target.tagName === 'TEXTAREA' || target.tagName === 'INPUT') {
      const start = target.selectionStart ?? target.value.length;
      const end = target.selectionEnd ?? target.value.length;
      target.value = target.value.slice(0, start) + text + target.value.slice(end);
      target.selectionStart = start + text.length;
      target.selectionEnd = start + text.length;
      target.dispatchEvent(new Event('input', { bubbles: true }));
      return true;
    }

    if (target.isContentEditable) {
      const selection = window.getSelection();
      const range = selection && selection.rangeCount ? selection.getRangeAt(0) : document.createRange();
      const node = document.createTextNode(text);
      if (selection && selection.rangeCount) {
        range.deleteContents();
        range.insertNode(node);
        range.setStartAfter(node);
        range.setEndAfter(node);
        selection.removeAllRanges();
        selection.addRange(range);
      } else {
        target.appendChild(node);
      }
      target.dispatchEvent(new Event('input', { bubbles: true }));
      return true;
    }

    return false;
  }

  function mergePresetModules(preset) {
    if (!preset || !Array.isArray(preset.modules)) return '';
    return preset.modules
      .filter((module) => module.enabled)
      .map((module) => module.content.trim())
      .filter(Boolean)
      .join('\n\n');
  }

  function renderPresetCards(state, panel) {
    const list = panel.querySelector('[data-role="preset-list"]');
    if (!list) return;

    list.innerHTML = '';

    state.presets.forEach((preset) => {
      const card = document.createElement('div');
      card.className = 'chub-toolkit-preset';
      if (preset.id === state.activePresetId) {
        card.classList.add('is-active');
      }

      const header = document.createElement('div');
      header.className = 'chub-toolkit-preset-header';
      header.innerHTML = '<strong>' + escapeHtml(preset.name) + '</strong>';

      const description = document.createElement('div');
      description.className = 'chub-toolkit-preset-description';
      description.textContent = preset.description || 'No description';

      const controls = document.createElement('div');
      controls.className = 'chub-toolkit-preset-controls';

      const selectBtn = document.createElement('button');
      selectBtn.type = 'button';
      selectBtn.textContent = 'Activate';
      selectBtn.addEventListener('click', () => {
        state.activePresetId = preset.id;
        writeState(state);
        renderPresetCards(state, panel);
      });

      const insertBtn = document.createElement('button');
      insertBtn.type = 'button';
      insertBtn.textContent = 'Insert';
      insertBtn.addEventListener('click', () => {
        const target = getTextInputTarget();
        const payload = mergePresetModules(preset);
        if (!target || !payload) return;
        setTextAtTarget(target, payload + '\n\n');
      });

      controls.append(selectBtn, insertBtn);
      card.append(header, description, controls);
      list.append(card);
    });
  }

  function escapeHtml(value) {
    return String(value)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  function createPanel() {
    const existing = document.getElementById(PANEL_ID);
    if (existing) return existing;

    const root = document.createElement('aside');
    root.id = PANEL_ID;
    root.style.position = 'fixed';
    root.style.right = '16px';
    root.style.top = '16px';
    root.style.zIndex = '2147483647';
    root.style.width = '320px';
    root.style.maxWidth = 'calc(100vw - 24px)';
    root.style.maxHeight = '80vh';
    root.style.overflow = 'auto';
    root.style.border = '1px solid rgba(255,255,255,0.1)';
    root.style.borderRadius = '14px';
    root.style.background = 'rgba(14, 18, 24, 0.96)';
    root.style.color = '#edf3ff';
    root.style.boxShadow = '0 18px 50px rgba(0,0,0,0.38)';
    root.style.fontFamily = 'system-ui, sans-serif';
    root.style.fontSize = '13px';
    root.style.padding = '12px';
    root.style.backdropFilter = 'blur(10px)';

    const title = document.createElement('div');
    title.innerHTML = '<strong>Chub Prompt Toolkit</strong>';
    title.style.marginBottom = '10px';
    title.style.fontSize = '14px';

    const state = readState();
    const activePreset = getActivePreset(state);

    const previewHolder = document.createElement('div');
    previewHolder.style.marginBottom = '10px';
    previewHolder.style.padding = '8px';
    previewHolder.style.border = '1px solid rgba(255,255,255,0.08)';
    previewHolder.style.borderRadius = '8px';
    previewHolder.style.background = 'rgba(255,255,255,0.02)';
    previewHolder.textContent = mergePresetModules(activePreset) || 'No active preset';
    previewHolder.style.whiteSpace = 'pre-wrap';

    const insertBtn = document.createElement('button');
    insertBtn.type = 'button';
    insertBtn.textContent = 'Insert active pack';
    insertBtn.style.width = '100%';
    insertBtn.style.marginBottom = '10px';
    insertBtn.addEventListener('click', () => {
      const target = getTextInputTarget();
      const payload = mergePresetModules(getActivePreset(readState()));
      if (!target || !payload) return;
      setTextAtTarget(target, payload + '\n\n');
    });

    const exportArea = document.createElement('textarea');
    exportArea.value = JSON.stringify(state, null, 2);
    exportArea.rows = 6;
    exportArea.style.width = '100%';
    exportArea.style.boxSizing = 'border-box';
    exportArea.style.marginBottom = '8px';
    exportArea.style.borderRadius = '8px';
    exportArea.style.border = '1px solid rgba(255,255,255,0.08)';
    exportArea.style.background = '#0a0d12';
    exportArea.style.color = '#edf3ff';

    const exportBtn = document.createElement('button');
    exportBtn.type = 'button';
    exportBtn.textContent = 'Export JSON';
    exportBtn.style.width = '100%';
    exportBtn.style.marginBottom = '8px';
    exportBtn.addEventListener('click', () => {
      exportArea.value = JSON.stringify(readState(), null, 2);
      exportArea.select();
      document.execCommand('copy');
    });

    const importBtn = document.createElement('button');
    importBtn.type = 'button';
    importBtn.textContent = 'Import JSON';
    importBtn.style.width = '100%';
    importBtn.style.marginBottom = '10px';
    importBtn.addEventListener('click', () => {
      try {
        const parsed = JSON.parse(exportArea.value);
        if (!parsed || !Array.isArray(parsed.presets)) {
          throw new Error('Invalid preset JSON');
        }
        writeState(parsed);
        location.reload();
      } catch (error) {
        alert('Import failed. Please provide a valid Chub Prompt Toolkit JSON export.');
      }
    });

    const presetList = document.createElement('div');
    presetList.dataset.role = 'preset-list';
    presetList.style.display = 'grid';
    presetList.style.gap = '8px';

    const listWrap = document.createElement('div');
    listWrap.style.marginTop = '8px';
    listWrap.appendChild(presetList);

    root.appendChild(title);
    root.appendChild(previewHolder);
    root.appendChild(insertBtn);
    root.appendChild(exportArea);
    root.appendChild(exportBtn);
    root.appendChild(importBtn);
    root.appendChild(listWrap);

    const closeBtn = document.createElement('button');
    closeBtn.type = 'button';
    closeBtn.textContent = 'Hide panel';
    closeBtn.style.marginTop = '10px';
    closeBtn.style.width = '100%';
    closeBtn.addEventListener('click', () => {
      root.style.display = 'none';
    });
    root.appendChild(closeBtn);

    document.body.appendChild(root);

    renderPresetCards(readState(), root);
    return root;
  }

  function start() {
    if (!location.href.startsWith('https://chub.ai/')) return;

    const panel = createPanel();
    const observer = new MutationObserver(() => {
      const state = readState();
      const activePreset = getActivePreset(state);
      const preview = panel.querySelector('div');
      const payload = mergePresetModules(activePreset);
      if (preview && preview.textContent && payload) {
        const previewNode = panel.childNodes[1];
        if (previewNode && previewNode.textContent !== payload) {
          previewNode.textContent = payload;
        }
      }
    });

    observer.observe(document.body, { childList: true, subtree: true });
  }

  start();
})();
