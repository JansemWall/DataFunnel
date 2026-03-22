import math
import os
import shutil
import subprocess
import sys
import threading
from datetime import datetime

import customtkinter as ctk
from tkinter import Canvas, filedialog, messagebox

import motor_dados
from atualizador import baixar_e_aplicar_update, verificar_nova_versao
from config import PASTA_ORIGENS, VERSAO_ATUAL, VERIFICAR_ATUALIZACAO_AUTOMATICA, inicializar_sistema

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")


class EntradaColunaAutocomplete(ctk.CTkFrame):
    def __init__(self, parent, colunas_disponiveis=None, comando_foco_proximo=None, **kwargs):
        super().__init__(parent, **kwargs)
        
        self.colunas_disponiveis = colunas_disponiveis or []
        self.comando_foco_proximo = comando_foco_proximo
        self.popup_lista = None
        
        self.textbox = ctk.CTkTextbox(self, height=70, wrap="word")
        self.textbox.pack(fill="x", expand=True)
        
        self.frame_sugestoes = ctk.CTkFrame(self, height=0, fg_color="transparent")
        self.frame_sugestoes.pack(fill="x", padx=0, pady=0)
        self.frame_sugestoes.pack_forget()
        
        cor_fundo_sugestoes = "#f9f9f9" if ctk.get_appearance_mode() == "Light" else "#2b2b2b"
        self.listbox_sugestoes = ctk.CTkTextbox(self.frame_sugestoes, height=150, wrap="none", fg_color=cor_fundo_sugestoes)
        self.listbox_sugestoes.pack(fill="both", expand=True, padx=2, pady=2)
        self.listbox_sugestoes.configure(state="disabled")
        
        bg_badge = "#d4edda" if ctk.get_appearance_mode() == "Light" else "#1a3b2a"
        fg_badge = "#1b5e20" if ctk.get_appearance_mode() == "Light" else "#2ecc71"
        self.textbox.tag_config("badge_valido", background=bg_badge, foreground=fg_badge)
        
        self.textbox.bind("<KeyRelease>", self._ao_digitar)
        self.textbox.bind("<Tab>", self._ao_tab)
        self.textbox.bind("<Escape>", self._ocultar_sugestoes)
        self.textbox.bind("<Up>", self._ao_arrow_up)
        self.textbox.bind("<Down>", self._ao_arrow_down)
        self.listbox_sugestoes._textbox.bind("<ButtonRelease-1>", self._ao_clicar_sugestao)
        
        self._sugestoes_atuais = []
        self._indice_selecionado = -1
    
    def _obter_palavra_atual(self) -> tuple[str, int, int]:
        conteudo = self.textbox.get("1.0", "end-1c")
        cursor_pos = self.textbox.index("insert")
        linha, coluna = map(int, cursor_pos.split("."))
        
        linhas = conteudo.split("\n")
        if linha > len(linhas):
            return "", 0, coluna
        
        linha_texto = linhas[linha - 1]
        
        inicio = coluna - 1
        while inicio >= 0 and linha_texto[inicio] not in (',', ' '):
            inicio -= 1
        
        inicio = max(0, inicio + 1 if inicio >= 0 and linha_texto[inicio] in (',', ' ') else inicio)
        palavra = linha_texto[inicio:coluna].strip()
        return palavra, linha, coluna
    
    def _obter_colunas_matches(self, termo: str) -> list[str]:
        if not termo:
            return []
        termo_lower = termo.lower()
        matches = [col for col in self.colunas_disponiveis if termo_lower in col.lower()]
        return matches[:10]
    
    def _atualizar_badges(self):
        self.textbox.tag_remove("badge_valido", "1.0", "end")
        texto = self.textbox.get("1.0", "end-1c")
        if not texto.strip() or not self.colunas_disponiveis:
            return

        colunas_validas = {c.lower() for c in self.colunas_disponiveis}
        
        linhas = texto.split('\n')
        for i, linha in enumerate(linhas):
            num_linha = i + 1
            partes = linha.split(',')
            col_atual = 0
            for parte in partes:
                termo = parte.strip()
                if termo and termo.lower() in colunas_validas:
                    inicio_termo = col_atual + parte.find(termo)
                    fim_termo = inicio_termo + len(termo)
                    
                    idx_inicio = f"{num_linha}.{inicio_termo}"
                    idx_fim = f"{num_linha}.{fim_termo}"
                    self.textbox.tag_add("badge_valido", idx_inicio, idx_fim)
                col_atual += len(parte) + 1
    
    def _ao_digitar(self, event=None):
        if event and event.keysym in ("Tab", "Up", "Down", "Return", "Escape", "Shift_L", "Shift_R"):
            return
            
        self._atualizar_badges()
        
        palavra, _, _ = self._obter_palavra_atual()
        if len(palavra) > 0:
            self._sugestoes_atuais = self._obter_colunas_matches(palavra)
            self._indice_selecionado = -1
            
            if self._sugestoes_atuais:
                self._mostrar_sugestoes()
            else:
                self._ocultar_sugestoes()
        else:
            self._ocultar_sugestoes()
    
    def _mostrar_sugestoes(self):
        self.listbox_sugestoes.configure(state="normal")
        self.listbox_sugestoes.delete("1.0", "end")
        
        palavra, _, _ = self._obter_palavra_atual()
        for i, sugestao in enumerate(self._sugestoes_atuais):
            eh_match_exato = sugestao.lower() == palavra.lower() if palavra else False
            badge = " ✓" if eh_match_exato else ""
            prefixo = "➜ " if i == self._indice_selecionado else "  "
            
            self.listbox_sugestoes.insert("end", f"{prefixo}{sugestao}{badge}\n")
            
        self.listbox_sugestoes.configure(state="disabled")
        
        qtd_itens = len(self._sugestoes_atuais)
        altura_ideal = min(qtd_itens * 28 + 6, 150)
        
        self.frame_sugestoes.configure(height=altura_ideal)
        self.frame_sugestoes.pack_propagate(False)
        self.frame_sugestoes.pack(fill="x", padx=0, pady=(2, 0))
    
    def _ocultar_sugestoes(self, event=None):
        self.frame_sugestoes.pack_forget()
        return "break"
    
    def _ao_tab(self, event):
        if self.frame_sugestoes.winfo_ismapped() and self._sugestoes_atuais:
            if self._indice_selecionado >= 0:
                self._inserir_sugestao(self._sugestoes_atuais[self._indice_selecionado])
            else:
                self._inserir_sugestao(self._sugestoes_atuais[0])
            return "break"
        elif self.comando_foco_proximo:
            return self.comando_foco_proximo(event)
    
    def _ao_arrow_down(self, event):
        if self._sugestoes_atuais:
            self._indice_selecionado = (self._indice_selecionado + 1) % len(self._sugestoes_atuais)
            self._mostrar_sugestoes()
            return "break"
    
    def _ao_arrow_up(self, event):
        if self._sugestoes_atuais:
            self._indice_selecionado = (self._indice_selecionado - 1) % len(self._sugestoes_atuais)
            self._mostrar_sugestoes()
            return "break"
            
    def _ao_clicar_sugestao(self, event):
        try:
            widget_tk = self.listbox_sugestoes._textbox
            indice_str = widget_tk.index(f"@{event.x},{event.y}")
            linha_clicada = int(indice_str.split('.')[0])
            
            texto_linha = self.listbox_sugestoes.get(f"{linha_clicada}.0", f"{linha_clicada}.end").strip()
            sugestao = texto_linha.replace("✓", "").replace("➜", "").strip()
            
            if sugestao:
                self._inserir_sugestao(sugestao)
        except Exception:
            pass
    
    def _inserir_sugestao(self, sugestao: str):
        palavra, linha, coluna = self._obter_palavra_atual()
        conteudo = self.textbox.get("1.0", "end-1c")
        
        inicio = max(0, coluna - len(palavra))
        linhas = conteudo.split("\n")
        linha_idx = linha - 1
        linha_texto = linhas[linha_idx] if linha_idx < len(linhas) else ""
        
        before = linha_texto[:inicio]
        after = linha_texto[coluna:]
        
        if not after.strip().startswith(","):
            novo_texto = before + sugestao + ", " + after
            offset_cursor = len(sugestao) + 2
        else:
            novo_texto = before + sugestao + after
            offset_cursor = len(sugestao)
            
        linhas[linha_idx] = novo_texto
        
        self.textbox.delete("1.0", "end")
        self.textbox.insert("1.0", "\n".join(linhas))
        self.textbox.mark_set("insert", f"{linha}.{inicio + offset_cursor}")
        
        self._ocultar_sugestoes()
        self._atualizar_badges()
    
    def atualizar_colunas(self, colunas: list[str]):
        self.colunas_disponiveis = colunas or []
        self._atualizar_badges()
    
    def get(self, *args):
        return self.textbox.get(*args)
    
    def insert(self, *args):
        ret = self.textbox.insert(*args)
        self._atualizar_badges()
        return ret
    
    def delete(self, *args):
        ret = self.textbox.delete(*args)
        self._atualizar_badges()
        return ret
    
    def bind(self, *args):
        return self.textbox.bind(*args)


class BuscadorApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        self.title(f"Sistema Avancado de Filtros de Dados - v{VERSAO_ATUAL}")
        self.geometry("750x850")

        self.caminho_base_ativa = ""
        self.is_base_no_cofre = False
        self.colunas_base_atual = [] 
        self.filtros_widgets = []
        self.stop_event = threading.Event()
        self.thread_processamento = None
        self.stop_event_conversao = threading.Event()
        self.thread_conversao = None
        self._id_conversao_ativa = 0
        self.total_chunks_conversao = 0
        self.chunks_concluidos = 0
        self._blocos_chunks_ids: list[int] = []
        self._limites_blocos_progresso: list[int] = []
        self._tamanho_bloco_padrao = 12
        self._tamanho_bloco_minimo = 3
        self._espaco_blocos = 2
        self._max_colunas_grade = 18
        self._total_etapas_grade = 0
        self._etapas_preparo = 4
        self._animacao_cancelamento_id: str | None = None
        self._animacao_cancelamento_indice = 0
        self._modo_progresso_popup = "preparo"
        self._progresso_preparo_atual = 0
        self._progresso_preparo_total = 1
        self._cancelamento_em_andamento = False
        self._popup_conversao_visivel = False
        self._id_limpeza_status: str | None = None
        
        self._loading_main_ativo = False
        self._loading_main_indice = 0
        self._loading_popup_ativo = False
        self._loading_popup_indice = 0

        self.overlay_conversao: ctk.CTkToplevel | None = None
        self.popup_conversao: ctk.CTkToplevel | None = None
        self.label_status_conversao: ctk.CTkLabel | None = None
        self.canvas_loading_main: Canvas | None = None
        self.canvas_loading_popup: Canvas | None = None
        self.canvas_chunks: Canvas | None = None
        self.btn_cancelar_conversao: ctk.CTkButton | None = None

        inicializar_sistema()

        self.label_titulo = ctk.CTkLabel(
            self,
            text="Filtro de Planilhas em Funil",
            font=ctk.CTkFont(size=22, weight="bold"),
        )
        self.label_titulo.pack(pady=(15, 5))

        self.tabview = ctk.CTkTabview(self, width=710, height=750)
        self.tabview.pack(padx=20, pady=10, fill="both", expand=True)

        self.tab_pesquisa = self.tabview.add("Pesquisa")
        self.tab_historico = self.tabview.add("Historico de Resultados")

        self.configurar_aba_pesquisa()
        self.configurar_aba_historico()

        self.tabview.configure(command=self.ao_mudar_aba)
        self.protocol("WM_DELETE_WINDOW", self.ao_fechar_aplicacao)
        self.bind("<Configure>", self._ao_mover_ou_redimensionar_janela)
        self.bind("<Unmap>", self._ao_minimizar_janela)
        self.bind("<Map>", self._ao_restaurar_janela)

        if getattr(sys, "frozen", False) and VERIFICAR_ATUALIZACAO_AUTOMATICA:
            self.after(2000, self.verificar_atualizacoes)

    def verificar_atualizacoes(self) -> None:
        thread = threading.Thread(target=self._checar_nuvem_background, daemon=True)
        thread.start()

    def _checar_nuvem_background(self) -> None:
        try:
            resultado = verificar_nova_versao(VERSAO_ATUAL)
            if resultado:
                versao_nuvem, url_download = resultado
                self.after(0, lambda: self.perguntar_atualizacao(versao_nuvem, url_download))
        except Exception:
            pass

    def perguntar_atualizacao(self, versao_nuvem: str, url_download: str) -> None:
        resposta = messagebox.askyesno(
            "Atualizacao Disponivel!",
            (
                f"Uma nova versao (v{versao_nuvem}) esta disponivel!\n\n"
                "Deseja atualizar agora? O sistema sera reiniciado rapidamente."
            ),
        )

        if resposta:
            self.label_titulo.configure(text="Baixando atualizacao, aguarde...", text_color="#f39c12")
            thread = threading.Thread(
                target=self._baixar_update_background,
                args=(url_download,),
                daemon=True,
            )
            thread.start()

    def _baixar_update_background(self, url_download: str) -> None:
        try:
            baixar_e_aplicar_update(url_download)
        except Exception as erro:
            self.after(
                0,
                lambda: messagebox.showerror(
                    "Erro na Atualizacao",
                    f"Falha ao baixar atualizacao: {str(erro)}",
                ),
            )
            self.after(
                0,
                lambda: self.label_titulo.configure(text="Filtro de Planilhas em Funil", text_color="white"),
            )

    def configurar_aba_pesquisa(self) -> None:
        frame_base = ctk.CTkFrame(self.tab_pesquisa, fg_color="transparent")
        frame_base.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(
            frame_base,
            text="1. Selecione a base de dados:",
            font=ctk.CTkFont(weight="bold"),
        ).pack(pady=(5, 2))

        self.bases_salvas = motor_dados.carregar_bases()
        opcoes_bases = ["+ Carregar novo arquivo do computador..."] + list(self.bases_salvas.keys())

        self.combo_bases = ctk.CTkOptionMenu(
            frame_base,
            values=opcoes_bases,
            command=self.ao_selecionar_base,
            width=400,
        )
        self.combo_bases.pack(pady=5)
        self.combo_bases.set("Selecione uma base...")

        self.frame_acoes_base = ctk.CTkFrame(frame_base, fg_color="transparent", height=28)

        self.btn_converter_sem_filtro = ctk.CTkButton(
            self.frame_acoes_base,
            text="Converter sem filtro",
            command=self.iniciar_conversao_sem_filtro,
            fg_color="transparent",
            hover_color="#2a2a2a",
            text_color="#5dade2",
            border_width=0,
            width=150,
            height=22,
            font=ctk.CTkFont(size=11, underline=True),
        )

        self.btn_exportar_csv_base = ctk.CTkButton(
            self.frame_acoes_base,
            text="Exportar CSV da base",
            command=self.exportar_csv_da_base,
            fg_color="transparent",
            hover_color="#2a2a2a",
            text_color="#7f8c8d",
            border_width=0,
            width=150,
            height=22,
            font=ctk.CTkFont(size=11, underline=True),
        )

        self.btn_converter_sem_filtro.pack(side="left", padx=8)
        self.btn_exportar_csv_base.pack(side="left", padx=8)
        self.btn_converter_sem_filtro.pack_forget()
        self.btn_exportar_csv_base.pack_forget()
        self.frame_acoes_base.pack_forget()

        self.label_arquivo = ctk.CTkLabel(frame_base, text="", text_color="gray")
        self.label_arquivo.pack()

        frame_regras_header = ctk.CTkFrame(self.tab_pesquisa, fg_color="transparent")
        frame_regras_header.pack(fill="x", padx=10, pady=(15, 0))

        ctk.CTkLabel(
            frame_regras_header,
            text="2. Regras de Busca:",
            font=ctk.CTkFont(weight="bold"),
        ).pack(side="left")

        self.btn_reutilizar = ctk.CTkButton(
            frame_regras_header,
            text="Reutilizar Filtros Anteriores",
            fg_color="#8e44ad",
            hover_color="#732d91",
            height=24,
            command=self.abrir_janela_reutilizar,
        )
        self.btn_reutilizar.pack(side="right")

        texto_ajuda = "Dica: Pode colar varias linhas copiadas do Excel! Separamos por virgula ou quebra de linha."
        ctk.CTkLabel(
            self.tab_pesquisa,
            text=texto_ajuda,
            text_color="#3498db",
            font=ctk.CTkFont(size=11),
        ).pack()

        self.frame_scroll_filtros = ctk.CTkScrollableFrame(
            self.tab_pesquisa,
            height=350,
            fg_color="transparent",
        )
        self.frame_scroll_filtros.pack(fill="both", expand=True, padx=10, pady=5)

        self.adicionar_linha_filtro()

        self.btn_add_filtro = ctk.CTkButton(
            self.tab_pesquisa,
            text="+ Adicionar Novo Filtro (AND / E)",
            command=self.adicionar_linha_filtro,
            fg_color="#34495e",
            hover_color="#2c3e50",
        )
        self.btn_add_filtro.pack(pady=5)

        self.btn_processar = ctk.CTkButton(
            self.tab_pesquisa,
            text="3. Pesquisar e Gerar Resultado",
            command=self.iniciar_processamento,
            fg_color="green",
            hover_color="darkgreen",
            height=40,
            font=ctk.CTkFont(weight="bold"),
        )
        self.btn_processar.pack(pady=15)

        self.frame_status = ctk.CTkFrame(self.tab_pesquisa, fg_color="transparent")
        self.frame_status.pack(fill="x", padx=20)

        self.label_status = ctk.CTkLabel(self.frame_status, text="", text_color="gray")
        self.label_status.pack()
        
        self.canvas_loading_main = Canvas(
            self.frame_status,
            width=400,
            height=30,
            highlightthickness=0,
            bg=self._cor_janela_tk()
        )

    def _hex_to_rgb(self, hex_color: str) -> tuple[int, int, int]:
        hex_color = str(hex_color).lstrip('#')
        if len(hex_color) == 3:
            hex_color = ''.join(c + c for c in hex_color)
        if len(hex_color) != 6:
            return (0, 0, 0)
        try:
            return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        except ValueError:
            return (0, 0, 0)

    def _rgb_to_hex(self, rgb: tuple[int, int, int]) -> str:
        return f"#{int(rgb[0]):02x}{int(rgb[1]):02x}{int(rgb[2]):02x}"

    def _mesclar_cores(self, cor_fundo: str, cor_frente: str, alpha: float) -> str:
        rgb_bg = self._hex_to_rgb(cor_fundo)
        rgb_fg = self._hex_to_rgb(cor_frente)
        r = rgb_bg[0] + (rgb_fg[0] - rgb_bg[0]) * alpha
        g = rgb_bg[1] + (rgb_fg[1] - rgb_bg[1]) * alpha
        b = rgb_bg[2] + (rgb_fg[2] - rgb_bg[2]) * alpha
        return self._rgb_to_hex((r, g, b))

    def _animar_losango(self, canvas: Canvas, attr_indice: str, attr_ativo: str) -> None:
        if not getattr(self, attr_ativo, False):
            try:
                canvas.delete("all")
            except Exception:
                pass
            return

        try:
            canvas.delete("all")
            largura = canvas.winfo_width()
            altura = canvas.winfo_height()
            if largura < 10: largura = 400
            if altura < 10: altura = 30

            indice = getattr(self, attr_indice, 0)
            setattr(self, attr_indice, indice + 1)
            
            ciclo = 60
            pos = indice % (2 * ciclo)
            progresso = pos / ciclo if pos < ciclo else 1.0 - ((pos - ciclo) / ciclo)
            easing = (math.sin((progresso - 0.5) * math.pi) + 1) / 2
            
            margem = 40
            x_centro = margem + (largura - 2 * margem) * easing
            y_centro = altura / 2
            
            cor_bg = self._cor_janela_tk()
            cor_neon = "#00e5ff" if ctk.get_appearance_mode() == "Dark" else "#00b8d4"
            
            rastro_qtd = 12
            for i in range(rastro_qtd, 0, -1):
                pos_passada = (indice - i * 2) % (2 * ciclo)
                prog_passado = pos_passada / ciclo if pos_passada < ciclo else 1.0 - ((pos_passada - ciclo) / ciclo)
                eas_passado = (math.sin((prog_passado - 0.5) * math.pi) + 1) / 2
                x_passado = margem + (largura - 2 * margem) * eas_passado
                
                fator = 1.0 - (i / rastro_qtd)
                alpha = fator * 0.5
                cor_rastro = self._mesclar_cores(cor_bg, cor_neon, alpha)
                
                rx = 14 * fator
                ry = 7 * fator
                canvas.create_polygon(
                    x_passado, y_centro - ry,
                    x_passado + rx, y_centro,
                    x_passado, y_centro + ry,
                    x_passado - rx, y_centro,
                    fill=cor_rastro, outline="", smooth=True
                )
            
            rx = 18
            ry = 9
            canvas.create_polygon(
                x_centro, y_centro - ry,
                x_centro + rx, y_centro,
                x_centro, y_centro + ry,
                x_centro - rx, y_centro,
                fill=cor_neon, outline="", smooth=True
            )
            
            self.after(20, lambda: self._animar_losango(canvas, attr_indice, attr_ativo))
        except Exception:
            pass

    def ao_selecionar_base(self, escolha: str) -> None:
        if escolha == "+ Carregar novo arquivo do computador...":
            caminho = filedialog.askopenfilename(filetypes=[("Arquivos de Dados", "*.csv *.xlsx *.xls")])
            if caminho:
                self.caminho_base_ativa = caminho
                self.is_base_no_cofre = False
                nome = os.path.basename(caminho)
                self.label_arquivo.configure(text=f"Arquivo externo selecionado: {nome}", text_color="#f39c12")
                self.combo_bases.set("Arquivo Externo Selecionado")
                self._carregar_colunas_base()
                self._atualizar_acoes_base_selecionada()
            else:
                self.combo_bases.set("Selecione uma base...")
                self._esconder_acoes_base()
        else:
            self.caminho_base_ativa = self.bases_salvas[escolha]
            self.is_base_no_cofre = True
            self.label_arquivo.configure(text=f"Base carregada do cache local: {escolha}", text_color="#2ecc71")
            self._carregar_colunas_base()
            self._atualizar_acoes_base_selecionada()
    
    def _carregar_colunas_base(self) -> None:
        if not self.caminho_base_ativa:
            self.colunas_base_atual = []
            return
        
        try:
            self.colunas_base_atual = motor_dados.carregar_colunas_cache(self.caminho_base_ativa)
            for filtro in self.filtros_widgets:
                entrada_coluna = filtro.get("entry_coluna")
                if entrada_coluna and hasattr(entrada_coluna, 'atualizar_colunas'):
                    entrada_coluna.atualizar_colunas(self.colunas_base_atual)
        except Exception as e:
            print(f"Erro ao carregar colunas: {e}")
            self.colunas_base_atual = []

    def _esconder_acoes_base(self) -> None:
        self.btn_converter_sem_filtro.pack_forget()
        self.btn_exportar_csv_base.pack_forget()
        self.frame_acoes_base.pack_forget()
        self._ocultar_popup_conversao()

    def _atualizar_acoes_base_selecionada(self) -> None:
        self.btn_converter_sem_filtro.pack_forget()
        self.btn_exportar_csv_base.pack_forget()
        self.frame_acoes_base.pack_forget()
        self._ocultar_popup_conversao()

        eh_excel_externo = (
            bool(self.caminho_base_ativa)
            and not self.is_base_no_cofre
            and self.caminho_base_ativa.lower().endswith((".xlsx", ".xls"))
        )

        eh_csv_convertido = (
            bool(self.caminho_base_ativa)
            and self.is_base_no_cofre
            and self.caminho_base_ativa.lower().endswith(".csv")
        )

        if eh_excel_externo:
            self.frame_acoes_base.pack(pady=(0, 2))
            self.btn_converter_sem_filtro.pack(side="left", padx=8)

        if eh_csv_convertido:
            self.frame_acoes_base.pack(pady=(0, 2))
            self.btn_exportar_csv_base.pack(side="left", padx=8)

    def _cor_janela_tk(self) -> str:
        cor = self.cget("fg_color")
        if isinstance(cor, (list, tuple)) and len(cor) >= 2:
            return cor[1] if ctk.get_appearance_mode() == "Dark" else cor[0]
        if isinstance(cor, str) and cor and cor != "transparent":
            return cor
        return "#1f1f1f" if ctk.get_appearance_mode() == "Dark" else "#f5f5f5"

    def _garantir_popup_conversao(self) -> None:
        if self.popup_conversao and self.popup_conversao.winfo_exists():
            return

        self.popup_conversao = ctk.CTkToplevel(self)
        self.popup_conversao.title("Conversao em andamento")
        self.popup_conversao.geometry("580x230")
        self.popup_conversao.transient(self)
        self.popup_conversao.attributes("-topmost", False)
        self.popup_conversao.protocol("WM_DELETE_WINDOW", self.cancelar_conversao)

        frame_popup = ctk.CTkFrame(self.popup_conversao)
        frame_popup.pack(fill="both", expand=True, padx=14, pady=14)

        self.label_status_conversao = ctk.CTkLabel(frame_popup, text="", text_color="gray")
        self.label_status_conversao.pack(anchor="center", pady=(4, 2))

        self.canvas_loading_popup = Canvas(
            frame_popup,
            width=480,
            height=30,
            highlightthickness=0,
            bg=self._cor_janela_tk(),
        )
        self.canvas_loading_popup.pack(anchor="center", pady=(8, 10))

        self.canvas_chunks = Canvas(
            frame_popup,
            width=520,
            height=110,
            highlightthickness=0,
            bg=self._cor_janela_tk(),
        )
        self.canvas_chunks.pack(anchor="center", pady=(4, 2))
        self.canvas_chunks.pack_forget()

        self.btn_cancelar_conversao = ctk.CTkButton(
            frame_popup,
            text="Cancelar conversao",
            command=self.cancelar_conversao,
            fg_color="#7f8c8d",
            hover_color="#616a6b",
            width=150,
            height=24,
        )
        self.btn_cancelar_conversao.pack(anchor="center", pady=(4, 2))

        self._centralizar_popup_conversao()

    def _mostrar_modo_preparo_popup(self) -> None:
        self._modo_progresso_popup = "preparo"
        if self.canvas_chunks:
            self.canvas_chunks.pack_forget()
        if self.canvas_loading_popup:
            self.canvas_loading_popup.pack(anchor="center", pady=(8, 10))
        self._loading_popup_ativo = True
        self._loading_popup_indice = 0
        self._animar_losango(self.canvas_loading_popup, "_loading_popup_indice", "_loading_popup_ativo")

    def _mostrar_modo_processamento_popup(self) -> None:
        self._modo_progresso_popup = "processamento"
        self._loading_popup_ativo = False
        if self.canvas_loading_popup:
            self.canvas_loading_popup.pack_forget()
        if self.canvas_chunks:
            self.canvas_chunks.pack(anchor="center", pady=(4, 2))

    def _garantir_overlay_conversao(self) -> None:
        if self.overlay_conversao and self.overlay_conversao.winfo_exists():
            return

        self.overlay_conversao = ctk.CTkToplevel(self)
        self.overlay_conversao.overrideredirect(True)
        self.overlay_conversao.attributes("-alpha", 0.35)
        self.overlay_conversao.configure(fg_color="black")
        self.overlay_conversao.transient(self)
        self.overlay_conversao.attributes("-topmost", False)

    def _centralizar_popup_conversao(self) -> None:
        if not self.popup_conversao or not self.popup_conversao.winfo_exists():
            return

        self.update_idletasks()
        self.popup_conversao.update_idletasks()

        largura = self.popup_conversao.winfo_width()
        altura = self.popup_conversao.winfo_height()

        x = self.winfo_rootx() + (self.winfo_width() // 2) - (largura // 2)
        y = self.winfo_rooty() + (self.winfo_height() // 2) - (altura // 2)
        self.popup_conversao.geometry(f"{largura}x{altura}+{max(x, 0)}+{max(y, 0)}")

    def _mostrar_popup_conversao(self) -> None:
        self._garantir_overlay_conversao()
        self._garantir_popup_conversao()
        if not self.popup_conversao:
            return

        if self.overlay_conversao and self.overlay_conversao.winfo_exists():
            self._reposicionar_overlay()
            self.overlay_conversao.deiconify()
            self.overlay_conversao.lift()

        self.popup_conversao.deiconify()
        self.popup_conversao.lift()
        self.popup_conversao.focus_force()
        self.popup_conversao.grab_set()
        self._centralizar_popup_conversao()
        self._popup_conversao_visivel = True

    def _ocultar_popup_conversao(self) -> None:
        self._loading_popup_ativo = False
        if self.popup_conversao and self.popup_conversao.winfo_exists():
            try:
                self.popup_conversao.grab_release()
            except Exception:
                pass
            self.popup_conversao.withdraw()

        if self.overlay_conversao and self.overlay_conversao.winfo_exists():
            self.overlay_conversao.withdraw()

        self._popup_conversao_visivel = False

    def _reposicionar_overlay(self) -> None:
        if not self.overlay_conversao or not self.overlay_conversao.winfo_exists():
            return

        self.update_idletasks()
        x = self.winfo_rootx()
        y = self.winfo_rooty()
        largura = self.winfo_width()
        altura = self.winfo_height()
        self.overlay_conversao.geometry(f"{largura}x{altura}+{max(x, 0)}+{max(y, 0)}")

    def _ao_mover_ou_redimensionar_janela(self, _event=None) -> None:
        if not self._popup_conversao_visivel:
            return
        if self.state() == "iconic":
            return

        self._reposicionar_overlay()
        self._centralizar_popup_conversao()

    def _ao_minimizar_janela(self, _event=None) -> None:
        if self.state() != "iconic":
            return

        if self.popup_conversao and self.popup_conversao.winfo_exists():
            self.popup_conversao.withdraw()
        if self.overlay_conversao and self.overlay_conversao.winfo_exists():
            self.overlay_conversao.withdraw()

    def _ao_restaurar_janela(self, _event=None) -> None:
        if not self._popup_conversao_visivel:
            return
        if self.state() == "iconic":
            return

        if self.overlay_conversao and self.overlay_conversao.winfo_exists():
            self._reposicionar_overlay()
            self.overlay_conversao.deiconify()
            self.overlay_conversao.lift()

        if self.popup_conversao and self.popup_conversao.winfo_exists():
            self.popup_conversao.deiconify()
            self.popup_conversao.lift()
            self.popup_conversao.grab_set()
            self._centralizar_popup_conversao()

    def _distribuir_etapas_em_blocos(self, total_etapas: int, total_blocos: int) -> list[int]:
        total_etapas = max(total_etapas, 1)
        total_blocos = max(total_blocos, 1)
        base = total_etapas // total_blocos
        resto = total_etapas % total_blocos

        limites: list[int] = []
        acumulado = 0
        for i in range(total_blocos):
            etapas_no_bloco = base + (1 if i < resto else 0)
            if etapas_no_bloco <= 0:
                limites.append(-1)
                continue
            acumulado += etapas_no_bloco
            limites.append(acumulado)

        return limites

    def _calcular_layout_grade(self, total_chunks: int, largura_canvas: int, altura_canvas: int) -> tuple[int, int, int, int, int]:
        total_chunks = max(total_chunks, 1)

        area_relativa = max((largura_canvas / max(altura_canvas, 1)), 1.0)
        colunas_ideais = int(math.sqrt(total_chunks * area_relativa))
        colunas_ideais = max(2, min(colunas_ideais, self._max_colunas_grade, total_chunks))

        melhor_layout: tuple[int, int, int] | None = None
        for deslocamento in range(-6, 7):
            colunas = colunas_ideais + deslocamento
            if colunas < 2:
                continue
            colunas = min(colunas, self._max_colunas_grade, total_chunks)
            linhas = max(math.ceil(total_chunks / colunas), 1)

            tamanho_por_largura = (largura_canvas - ((colunas - 1) * self._espaco_blocos)) // colunas
            tamanho_por_altura = (altura_canvas - ((linhas - 1) * self._espaco_blocos)) // linhas
            tamanho = min(tamanho_por_largura, tamanho_por_altura, self._tamanho_bloco_padrao)

            if tamanho < self._tamanho_bloco_minimo:
                continue

            if not melhor_layout or tamanho > melhor_layout[2]:
                melhor_layout = (colunas, linhas, tamanho)

        if melhor_layout:
            colunas, _linhas, tamanho = melhor_layout
            return total_chunks, colunas, tamanho, self._espaco_blocos, total_chunks

        tamanho = self._tamanho_bloco_minimo
        passo = tamanho + self._espaco_blocos
        colunas = max((largura_canvas + self._espaco_blocos) // passo, 1)
        linhas = max((altura_canvas + self._espaco_blocos) // passo, 1)
        capacidade = max(colunas * linhas, 1)
        return capacidade, colunas, tamanho, self._espaco_blocos, total_chunks

    def _desenhar_grade_chunks(self, total_chunks: int) -> None:
        self._garantir_popup_conversao()
        if not self.canvas_chunks:
            return

        self.canvas_chunks.delete("all")
        self._blocos_chunks_ids = []
        self._total_etapas_grade = max(total_chunks, 1)

        cor_fundo = "#0d1117" if ctk.get_appearance_mode() == "Dark" else "#f3f4f6"
        cor_bloco_vazio = "#161b22" if ctk.get_appearance_mode() == "Dark" else "#d1d5db"
        cor_contorno = "#30363d" if ctk.get_appearance_mode() == "Dark" else "#9ca3af"

        self.canvas_chunks.configure(bg=cor_fundo)

        largura_canvas = max(self.canvas_chunks.winfo_width(), int(self.canvas_chunks.cget("width")))
        altura_canvas = max(self.canvas_chunks.winfo_height(), int(self.canvas_chunks.cget("height")))
        total_blocos, colunas, tamanho, espaco, total_representado = self._calcular_layout_grade(
            total_chunks,
            largura_canvas,
            altura_canvas,
        )
        self._limites_blocos_progresso = self._distribuir_etapas_em_blocos(total_representado, total_blocos)

        linhas_usadas = max(math.ceil(total_blocos / colunas), 1)
        largura_grade = (colunas * tamanho) + ((colunas - 1) * espaco)
        altura_grade = (linhas_usadas * tamanho) + ((linhas_usadas - 1) * espaco)
        inicio_x = max((largura_canvas - largura_grade) // 2, 6)
        inicio_y = max((altura_canvas - altura_grade) // 2, 6)

        for i in range(total_blocos):
            coluna = i % colunas
            linha = i // colunas
            x1 = inicio_x + coluna * (tamanho + espaco)
            y1 = inicio_y + linha * (tamanho + espaco)
            x2 = x1 + tamanho
            y2 = y1 + tamanho
            bloco_id = self.canvas_chunks.create_rectangle(
                x1,
                y1,
                x2,
                y2,
                fill=cor_bloco_vazio,
                outline=cor_contorno,
                width=1,
            )
            self._blocos_chunks_ids.append(bloco_id)

    def _cor_bloco_concluido(self, indice: int, concluidos: int) -> str:
        if concluidos <= 1:
            return "#2ea043"

        intensidade = int((indice / max(concluidos - 1, 1)) * 3)
        paleta = ["#2ea043", "#26a641", "#39d353", "#56d364"]
        return paleta[min(max(intensidade, 0), 3)]

    def _atualizar_grade_chunks(self, concluidos: int, total_chunks: int) -> None:
        if not self._blocos_chunks_ids:
            self._desenhar_grade_chunks(total_chunks)

        if max(total_chunks, 1) != self._total_etapas_grade:
            self._desenhar_grade_chunks(total_chunks)

        if not self.canvas_chunks or not self.label_status_conversao:
            return

        concluidos = max(0, min(concluidos, max(total_chunks, 1)))
        blocos_preenchidos = 0
        for limite in self._limites_blocos_progresso:
            if limite == -1:
                continue
            if concluidos >= limite:
                blocos_preenchidos += 1

        for i, bloco_id in enumerate(self._blocos_chunks_ids):
            if i < blocos_preenchidos:
                cor = self._cor_bloco_concluido(i, max(blocos_preenchidos, 1))
            else:
                cor = "#161b22" if ctk.get_appearance_mode() == "Dark" else "#d1d5db"
            self.canvas_chunks.itemconfigure(bloco_id, fill=cor)

        self.label_status_conversao.configure(
            text=f"Progresso: {concluidos}/{max(total_chunks, 1)}",
            text_color="#2ecc71" if concluidos >= total_chunks else "#95a5a6",
        )

    def iniciar_conversao_sem_filtro(self) -> None:
        if not self.caminho_base_ativa:
            messagebox.showwarning("Aviso", "Selecione uma base para converter.")
            return

        if self.thread_conversao and self.thread_conversao.is_alive() and not self.stop_event_conversao.is_set():
            messagebox.showinfo("Aviso", "Ja existe uma conversao em andamento.")
            return

        if not self.caminho_base_ativa.lower().endswith((".xlsx", ".xls")):
            messagebox.showinfo("Aviso", "Conversao sem filtro so e necessaria para arquivos Excel.")
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        caminho_destino = os.path.join(PASTA_ORIGENS, f"origem_{timestamp}.csv")
        nome_original = os.path.basename(self.caminho_base_ativa)

        self.combo_bases.configure(state="disabled")
        self.btn_processar.configure(state="disabled", fg_color="gray")
        self.btn_add_filtro.configure(state="disabled")
        self.btn_converter_sem_filtro.configure(state="disabled")
        self.btn_exportar_csv_base.configure(state="disabled")

        self._id_conversao_ativa += 1
        id_conversao = self._id_conversao_ativa
        stop_event_conversao = threading.Event()
        self.stop_event_conversao = stop_event_conversao
        self._cancelamento_em_andamento = False
        self._parar_animacao_cancelamento()
        self.total_chunks_conversao = 0
        self.chunks_concluidos = 0
        self._mostrar_popup_conversao()
        self._mostrar_modo_preparo_popup()

        if self.popup_conversao:
            self.popup_conversao.title("Conversao em andamento")
        if self.btn_cancelar_conversao:
            self.btn_cancelar_conversao.configure(text="Cancelar conversao", command=self.cancelar_conversao)

        if self.label_status_conversao:
            self.label_status_conversao.configure(text="Preparando conversao...", text_color="#95a5a6")

        self.thread_conversao = threading.Thread(
            target=self._converter_base_background,
            args=(self.caminho_base_ativa, caminho_destino, nome_original, stop_event_conversao, id_conversao),
            daemon=True,
        )
        self.thread_conversao.start()

    def _converter_base_background(
        self,
        caminho_excel: str,
        caminho_destino: str,
        nome_original: str,
        stop_event_conversao: threading.Event,
        id_conversao: int,
    ) -> None:
        try:
            def atualizar_status(txt: str) -> None:
                if stop_event_conversao.is_set() or id_conversao != self._id_conversao_ativa:
                    return
                if self.winfo_exists() and self.label_status_conversao:
                    self.after(0, lambda t=txt: self.label_status_conversao.configure(text=t, text_color="#95a5a6"))

            def atualizar_progresso(concluidos: int, total: int) -> None:
                if stop_event_conversao.is_set() or id_conversao != self._id_conversao_ativa:
                    return
                self.total_chunks_conversao = total
                self.chunks_concluidos = concluidos
                if self.winfo_exists():
                    self.after(0, lambda c=concluidos, t=total: self._atualizar_visual_progresso(c, t))

            linhas_convertidas, _ = motor_dados.converter_excel_para_csv_em_lotes(
                caminho_excel,
                caminho_destino,
                stop_event=stop_event_conversao,
                status_callback=atualizar_status,
                progresso_callback=atualizar_progresso,
            )

            if stop_event_conversao.is_set() or id_conversao != self._id_conversao_ativa:
                raise RuntimeError("PROCESSAMENTO_CANCELADO")

            self.bases_salvas, base_nome = motor_dados.salvar_nova_base(
                self.bases_salvas,
                nome_original,
                caminho_destino,
            )

            data_hora_agora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            motor_dados.registrar_conversao_historico(
                timestamp, 
                data_hora_agora, 
                nome_original, 
                caminho_destino, 
                linhas_convertidas
            )

            self.caminho_base_ativa = caminho_destino
            self.is_base_no_cofre = True

            if self.winfo_exists() and id_conversao == self._id_conversao_ativa:
                self.after(0, lambda n=base_nome: self._finalizar_conversao_com_sucesso(n))

        except RuntimeError as erro:
            if str(erro) == "PROCESSAMENTO_CANCELADO":
                if os.path.exists(caminho_destino):
                    os.remove(caminho_destino)
                if self.winfo_exists() and id_conversao == self._id_conversao_ativa:
                    self.after(0, self._finalizar_conversao_cancelada)
                return
            if os.path.exists(caminho_destino):
                os.remove(caminho_destino)
            if self.winfo_exists() and id_conversao == self._id_conversao_ativa:
                self.after(0, lambda e=erro: self._falha_conversao(str(e)))
        except Exception as erro:
            if os.path.exists(caminho_destino):
                os.remove(caminho_destino)
            if self.winfo_exists() and id_conversao == self._id_conversao_ativa:
                self.after(0, lambda e=erro: self._falha_conversao(str(e)))
        finally:
            if self.winfo_exists() and id_conversao == self._id_conversao_ativa:
                self.after(0, self._restaurar_interface_conversao)

    def _atualizar_visual_progresso(self, concluidos: int, total: int) -> None:
        total = max(total, 1)
        etapas_preparo = min(self._etapas_preparo, total)

        if concluidos <= etapas_preparo:
            self._mostrar_modo_preparo_popup()
            self._progresso_preparo_atual = concluidos
            self._progresso_preparo_total = etapas_preparo
            return

        concluidos_processamento = max(concluidos - etapas_preparo, 0)
        total_processamento = max(total - etapas_preparo, 1)

        if self._modo_progresso_popup != "processamento":
            self._mostrar_modo_processamento_popup()
            self._desenhar_grade_chunks(total_processamento)

        self._atualizar_grade_chunks(concluidos_processamento, total_processamento)

    def cancelar_conversao(self) -> None:
        if self._cancelamento_em_andamento:
            return

        self.stop_event_conversao.set()
        self._cancelamento_em_andamento = True

        self._ocultar_popup_conversao()
        self._restaurar_interface_conversao()

    def _finalizar_conversao_com_sucesso(self, base_nome: str) -> None:
        self.combo_bases.configure(values=["+ Carregar novo arquivo do computador..."] + list(self.bases_salvas.keys()))
        self.combo_bases.set(base_nome)
        self.label_arquivo.configure(text=f"Base convertida para CSV e carregada: {base_nome}", text_color="#2ecc71")
        self._atualizar_grade_chunks(self.total_chunks_conversao, self.total_chunks_conversao)
        self._ocultar_popup_conversao()
        self._carregar_colunas_base()
        self._atualizar_acoes_base_selecionada()

    def _finalizar_conversao_cancelada(self) -> None:
        self._parar_animacao_cancelamento()
        self._ocultar_popup_conversao()

    def _falha_conversao(self, erro: str) -> None:
        if self.label_status_conversao:
            self.label_status_conversao.configure(text="Erro na conversao.", text_color="#e74c3c")
        self._ocultar_popup_conversao()
        messagebox.showerror("Erro", f"Nao foi possivel converter a base:\n{erro}")

    def _restaurar_interface_conversao(self) -> None:
        self._parar_animacao_cancelamento()
        self._loading_popup_ativo = False
        self.combo_bases.configure(state="normal")
        self.btn_processar.configure(state="normal", fg_color="green")
        self.btn_add_filtro.configure(state="normal")
        self.btn_converter_sem_filtro.configure(state="normal")
        self.btn_exportar_csv_base.configure(state="normal")
        if self.btn_cancelar_conversao:
            self.btn_cancelar_conversao.configure(state="normal", text="Cancelar conversao")
        self._cancelamento_em_andamento = False

    def _iniciar_animacao_cancelamento(self) -> None:
        self._animacao_cancelamento_indice = 0
        self._animar_cancelamento()

    def _animar_cancelamento(self) -> None:
        if not self._cancelamento_em_andamento or not self._blocos_chunks_ids or not self.canvas_chunks:
            return

        cor_base = "#161b22" if ctk.get_appearance_mode() == "Dark" else "#d1d5db"

        for bloco_id in self._blocos_chunks_ids:
            self.canvas_chunks.itemconfigure(bloco_id, fill=cor_base)

        janela_animacao = 8
        for passo in range(janela_animacao):
            indice = (self._animacao_cancelamento_indice + passo) % len(self._blocos_chunks_ids)
            self.canvas_chunks.itemconfigure(self._blocos_chunks_ids[indice], fill="#f39c12")

        pontos = "." * ((self._animacao_cancelamento_indice % 3) + 1)
        if self.label_status_conversao:
            self.label_status_conversao.configure(text=f"Cancelando conversao{pontos}", text_color="#f39c12")

        self._animacao_cancelamento_indice += 1
        self._animacao_cancelamento_id = self.after(120, self._animar_cancelamento)

    def _parar_animacao_cancelamento(self) -> None:
        self._cancelamento_em_andamento = False
        if self._animacao_cancelamento_id:
            self.after_cancel(self._animacao_cancelamento_id)
            self._animacao_cancelamento_id = None

    def exportar_csv_da_base(self) -> None:
        if not self.caminho_base_ativa or not self.is_base_no_cofre:
            messagebox.showwarning("Aviso", "Selecione uma base convertida para exportar o CSV.")
            return

        if not self.caminho_base_ativa.lower().endswith(".csv") or not os.path.exists(self.caminho_base_ativa):
            messagebox.showwarning("Aviso", "A base selecionada nao possui CSV disponivel para exportacao.")
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        nome_base = os.path.splitext(os.path.basename(self.caminho_base_ativa))[0]
        nome_sugerido = f"CSV_Base_{nome_base}_{timestamp}.csv"

        caminho_salvar = filedialog.asksaveasfilename(
            title="Exportar CSV da base",
            defaultextension=".csv",
            initialfile=nome_sugerido,
            filetypes=[("CSV", "*.csv"), ("Todos os arquivos", "*.*")],
        )

        if not caminho_salvar:
            return

        try:
            shutil.copy2(self.caminho_base_ativa, caminho_salvar)
            messagebox.showinfo("Sucesso", "CSV da base exportado com sucesso!")
        except Exception as erro:
            messagebox.showerror("Erro", f"Falha ao exportar CSV da base:\n{str(erro)}")

    def abrir_janela_reutilizar(self) -> None:
        historico = motor_dados.carregar_historico()
        historico_com_regras = [h for h in historico if "regras_raw" in h]

        if not historico_com_regras:
            messagebox.showinfo("Aviso", "Nenhum historico de filtros encontrado ainda.")
            return

        janela = ctk.CTkToplevel(self)
        janela.title("Reutilizar Filtros Anteriores")
        janela.geometry("600x400")
        janela.transient(self)

        ctk.CTkLabel(
            janela,
            text="Selecione uma pesquisa anterior para reutilizar os filtros:",
            font=ctk.CTkFont(weight="bold"),
        ).pack(pady=10)

        frame_lista = ctk.CTkScrollableFrame(janela, width=550, height=300)
        frame_lista.pack(padx=10, pady=5, fill="both", expand=True)

        for item in historico_com_regras[:15]:
            btn = ctk.CTkButton(
                frame_lista,
                text=f"{item['data_hora']} | Busca: {item['termos'][:60]}...",
                anchor="w",
                fg_color="#34495e",
                hover_color="#2c3e50",
                command=lambda regras=item["regras_raw"], j=janela: self.aplicar_regras_salvas(regras, j),
            )
            btn.pack(fill="x", pady=2, padx=5)

    def aplicar_regras_salvas(self, regras_raw: list[dict[str, str]], janela: ctk.CTkToplevel) -> None:
        for filtro in self.filtros_widgets:
            filtro["frame_container"].destroy()
        self.filtros_widgets.clear()

        for regra in regras_raw:
            widgets = self.adicionar_linha_filtro()
            widgets["entry_coluna"].insert("1.0", regra["colunas"])
            widgets["entry_termos"].insert("1.0", regra["termos"])

        janela.destroy()

    def adicionar_linha_filtro(self) -> dict:
        indice = len(self.filtros_widgets) + 1

        linha_frame_container = ctk.CTkFrame(
            self.frame_scroll_filtros,
            fg_color="#1a1a1a" if ctk.get_appearance_mode() == "Dark" else "#f0f0f0",
        )
        linha_frame_container.pack(fill="x", pady=5)

        inner_frame = ctk.CTkFrame(linha_frame_container, fg_color="transparent")
        inner_frame.pack(anchor="center", pady=5, padx=5, fill="x")

        frame_topo = ctk.CTkFrame(inner_frame, fg_color="transparent")
        frame_topo.pack(fill="x")

        lbl_titulo_linha = ctk.CTkLabel(
            frame_topo,
            text=f"Regra {indice}:",
            font=ctk.CTkFont(weight="bold", size=14),
        )
        lbl_titulo_linha.pack(side="left", padx=5)

        if indice > 1:
            btn_remover = ctk.CTkButton(
                frame_topo,
                text="Remover regra",
                width=100,
                fg_color="#e74c3c",
                hover_color="#c0392b",
                height=24,
                command=lambda f=linha_frame_container: self.remover_linha_filtro(f),
            )
            btn_remover.pack(side="right", padx=5)

        frame_inputs = ctk.CTkFrame(inner_frame, fg_color="transparent")
        frame_inputs.pack(fill="x", pady=5)

        frame_col = ctk.CTkFrame(frame_inputs, fg_color="transparent")
        frame_col.pack(side="left", fill="both", expand=True, padx=(5, 10))
        ctk.CTkLabel(frame_col, text="Na(s) coluna(s) (ex.: Nome, Cargo):").pack(anchor="w")
        
        entry_col = EntradaColunaAutocomplete(
            frame_col,
            colunas_disponiveis=self.colunas_base_atual,
            fg_color="transparent",
            comando_foco_proximo=self._ao_tab_campo_filtro
        )
        entry_col.pack(fill="x")
        entry_col.textbox.bind("<Shift-Tab>", self._ao_shift_tab_campo_filtro)

        frame_term = ctk.CTkFrame(frame_inputs, fg_color="transparent")
        frame_term.pack(side="right", fill="both", expand=True, padx=(0, 5))
        ctk.CTkLabel(frame_term, text="Procurar termo(s) (cole a lista aqui):").pack(anchor="w")
        entry_term = ctk.CTkTextbox(frame_term, height=70, wrap="word")
        entry_term.pack(fill="x")
        
        entry_term.bind("<Tab>", self._ao_tab_campo_filtro)
        entry_term.bind("<Shift-Tab>", self._ao_shift_tab_campo_filtro)

        novo_widget = {
            "frame_container": linha_frame_container,
            "entry_coluna": entry_col,
            "entry_termos": entry_term,
            "label_titulo": lbl_titulo_linha,
        }
        self.filtros_widgets.append(novo_widget)
        return novo_widget

    def _campos_filtros_em_ordem(self) -> list:
        campos: list = []
        for filtro in self.filtros_widgets:
            entry_coluna = filtro.get("entry_coluna")
            entry_termos = filtro.get("entry_termos")
            if entry_coluna and entry_coluna.winfo_exists():
                widget_coluna = getattr(entry_coluna, "textbox", entry_coluna)
                campos.append(widget_coluna)
            if entry_termos and entry_termos.winfo_exists():
                widget_termos = getattr(entry_termos, "_textbox", entry_termos)
                if not widget_termos:
                    widget_termos = entry_termos
                campos.append(widget_termos)
        return campos

    def _mover_foco_entre_campos(self, widget_atual, direcao: int) -> None:
        campos = self._campos_filtros_em_ordem()
        if not campos:
            return

        widget_normalizado = getattr(widget_atual, "_textbox", widget_atual)

        try:
            indice_atual = campos.index(widget_normalizado)
        except ValueError:
            campos[0].focus_set()
            return

        proximo_indice = (indice_atual + direcao) % len(campos)
        campos[proximo_indice].focus_set()

    def _ao_tab_campo_filtro(self, event=None) -> str:
        if event and hasattr(event, "widget"):
            self._mover_foco_entre_campos(event.widget, 1)
        return "break"

    def _ao_shift_tab_campo_filtro(self, event=None) -> str:
        if event and hasattr(event, "widget"):
            self._mover_foco_entre_campos(event.widget, -1)
        return "break"

    def _cancelar_limpeza_status_agendada(self) -> None:
        if self._id_limpeza_status:
            try:
                self.after_cancel(self._id_limpeza_status)
            except Exception:
                pass
            self._id_limpeza_status = None

    def _agendar_limpeza_status_concluido(self) -> None:
        self._cancelar_limpeza_status_agendada()

        def limpar() -> None:
            self._id_limpeza_status = None
            if self.label_status and self.label_status.cget("text") == "Concluido!":
                self.label_status.configure(text="", text_color="gray")

        self._id_limpeza_status = self.after(30_000, limpar)

    def _atualizar_status_principal(self, texto: str, cor: str = "gray") -> None:
        if self.winfo_exists() and self.label_status:
            self.after(0, lambda: self.label_status.configure(text=texto, text_color=cor))

    def _atualizar_popup_progresso_filtro(self, concluidos: int, total: int) -> None:
        if not self.winfo_exists():
            return

        self.total_chunks_conversao = max(total, 1)
        self.chunks_concluidos = max(0, concluidos)

        def _renderizar() -> None:
            self._mostrar_modo_processamento_popup()
            self._atualizar_grade_chunks(self.chunks_concluidos, self.total_chunks_conversao)

        self.after(0, _renderizar)

    def cancelar_processamento(self) -> None:
        self.stop_event.set()
        self._ocultar_popup_conversao()
        self.restaurar_interface()
        self._atualizar_status_principal("Processamento cancelado.", "#f39c12")

    def remover_linha_filtro(self, frame_container_para_remover: ctk.CTkFrame) -> None:
        frame_container_para_remover.destroy()
        self.filtros_widgets = [
            f for f in self.filtros_widgets if f["frame_container"] != frame_container_para_remover
        ]
        for i, filtro in enumerate(self.filtros_widgets):
            filtro["label_titulo"].configure(text=f"Regra {i + 1}:")

    def iniciar_processamento(self) -> None:
        if not self.caminho_base_ativa:
            messagebox.showwarning("Aviso", "Por favor, selecione ou carregue uma base de dados primeiro.")
            return

        if self.thread_processamento and self.thread_processamento.is_alive():
            messagebox.showinfo("Aviso", "Ja existe um processamento em execucao.")
            return

        regras_validas = []
        for widget_set in self.filtros_widgets:
            colunas_raw = widget_set["entry_coluna"].get("1.0", "end-1c").strip()
            termos_raw = widget_set["entry_termos"].get("1.0", "end-1c").strip()

            termos_formatados = termos_raw.replace("\n", ",").replace(";", ",")
            colunas_formatadas = colunas_raw.replace("\n", ",").replace(";", ",")

            if termos_formatados:
                regras_validas.append({"colunas": colunas_formatadas, "termos": termos_formatados})

        if not regras_validas:
            messagebox.showwarning("Aviso", "Por favor, preencha os termos de pelo menos uma regra!")
            return

        self.btn_processar.configure(state="disabled", fg_color="gray")
        self.combo_bases.configure(state="disabled")
        self.btn_add_filtro.configure(state="disabled")
        self.btn_converter_sem_filtro.configure(state="disabled")
        self.btn_exportar_csv_base.configure(state="disabled")
        self._cancelar_limpeza_status_agendada()
        self.label_status.configure(text="Iniciando processamento...", text_color="white")

        if self.canvas_loading_main:
            self.canvas_loading_main.pack(pady=5)
        self._loading_main_ativo = True
        self._loading_main_indice = 0
        self._animar_losango(self.canvas_loading_main, "_loading_main_indice", "_loading_main_ativo")

        self.total_chunks_conversao = 0
        self.chunks_concluidos = 0
        self._mostrar_popup_conversao()
        self._mostrar_modo_processamento_popup()
        self._desenhar_grade_chunks(1)
        if self.popup_conversao:
            self.popup_conversao.title("Processamento em andamento")
        if self.btn_cancelar_conversao:
            self.btn_cancelar_conversao.configure(text="Cancelar processamento", command=self.cancelar_processamento)
        if self.label_status_conversao:
            self.label_status_conversao.configure(text="Aplicando filtros em lotes...", text_color="#95a5a6")

        self.stop_event.clear()
        self.thread_processamento = threading.Thread(
            target=self.processar_dados_background,
            args=(regras_validas,),
            daemon=True,
        )
        self.thread_processamento.start()

    def processar_dados_background(self, regras_de_busca: list[dict[str, str]]) -> None:
        try:
            if self.stop_event.is_set():
                return

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            data_hora_formatada = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

            (
                caminho_origem_imutavel,
                nome_original,
                self.is_base_no_cofre,
                self.bases_salvas,
            ) = motor_dados.preparar_base(
                self.caminho_base_ativa,
                self.is_base_no_cofre,
                self.bases_salvas,
                timestamp,
                status_callback=lambda txt: self._atualizar_status_principal(txt),
            )

            df_filtrado = motor_dados.filtrar_em_lotes(
                caminho_origem_imutavel,
                regras_de_busca,
                stop_event=self.stop_event,
                status_callback=lambda txt: self._atualizar_status_principal(txt),
                progresso_callback=lambda concluidos, total: self._atualizar_popup_progresso_filtro(concluidos, total),
            )

            qtd_linhas = len(df_filtrado)

            self._atualizar_status_principal("Salvando resultado e historico...")
            caminho_resultado_imutavel = motor_dados.salvar_resultado_csv(df_filtrado, timestamp)

            self._atualizar_status_principal("Exportando arquivo final...")
            nome_exportacao = motor_dados.gerar_nome_exportacao(regras_de_busca, timestamp)
            caminho_exportacao = filedialog.asksaveasfilename(
                title="Onde deseja salvar o Excel filtrado?",
                defaultextension=".xlsx",
                initialfile=nome_exportacao,
                filetypes=[("Excel", "*.xlsx")],
            )

            if caminho_exportacao:
                motor_dados.exportar_dataframe_excel(df_filtrado, caminho_exportacao)
            else:
                caminho_exportacao = ""

            motor_dados.registrar_execucao_historico(
                timestamp=timestamp,
                data_hora_formatada=data_hora_formatada,
                nome_original=nome_original,
                caminho_origem_imutavel=caminho_origem_imutavel,
                caminho_resultado_imutavel=caminho_resultado_imutavel,
                caminho_exportacao=caminho_exportacao,
                regras_de_busca=regras_de_busca,
                qtd_linhas=qtd_linhas,
            )

            self._atualizar_status_principal("Concluido!", "green")
            if self.winfo_exists():
                self.after(0, self._agendar_limpeza_status_concluido)

            if self.winfo_exists():
                self.after(0, lambda: self.finalizar_sucesso_transicao(timestamp))

        except RuntimeError as erro:
            if str(erro) != "PROCESSAMENTO_CANCELADO":
                self._atualizar_status_principal("Erro!", "red")
                if self.winfo_exists():
                    self.after(
                        0,
                        lambda e=erro: messagebox.showerror(
                            "Erro de Processamento",
                            f"Ocorreu um erro critico:\n{str(e)}",
                        ),
                    )
            else:
                self._atualizar_status_principal("Processamento cancelado.", "#f39c12")
        except Exception as erro:
            self._atualizar_status_principal("Erro!", "red")
            if self.winfo_exists():
                self.after(
                    0,
                    lambda e=erro: messagebox.showerror(
                        "Erro de Processamento",
                        f"Ocorreu um erro critico:\n{str(e)}",
                    ),
                )
        finally:
            if self.winfo_exists():
                self.after(0, self._ocultar_popup_conversao)
                self.after(0, self.restaurar_interface)

    def ao_fechar_aplicacao(self) -> None:
        self.stop_event.set()
        self.stop_event_conversao.set()
        self._ocultar_popup_conversao()

        if self.thread_processamento and self.thread_processamento.is_alive():
            self.thread_processamento.join(timeout=2)

        if self.thread_conversao and self.thread_conversao.is_alive():
            self.thread_conversao.join(timeout=2)

        self.destroy()

    def finalizar_sucesso_transicao(self, id_recente: str) -> None:
        self.restaurar_interface()
        self.tabview.set("Historico de Resultados")
        self.carregar_historico(destaque_id=id_recente)

    def configurar_aba_historico(self) -> None:
        self.frame_lista = ctk.CTkScrollableFrame(self.tab_historico, width=650, height=650)
        self.frame_lista.pack(padx=10, pady=10, fill="both", expand=True)

    def ao_mudar_aba(self) -> None:
        if self.tabview.get() == "Historico de Resultados":
            self.carregar_historico()

    def carregar_historico(self, destaque_id: str | None = None) -> None:
        for widget in self.frame_lista.winfo_children():
            widget.destroy()

        try:
            historico = motor_dados.carregar_historico()

            if not historico:
                ctk.CTkLabel(
                    self.frame_lista,
                    text="Nenhum historico encontrado ainda.",
                    text_color="gray",
                ).pack(pady=20)
                return

            for item in historico:
                is_recente = item["id"] == destaque_id
                cor_fundo = "#1a3b2a" if is_recente else (
                    "#2b2b2b" if ctk.get_appearance_mode() == "Dark" else "#e0e0e0"
                )

                card = ctk.CTkFrame(self.frame_lista, fg_color=cor_fundo)
                card.pack(fill="x", pady=5, padx=5)

                tag_recente = " (Gerado agora!)" if is_recente else ""
                texto_info = (
                    f"Data: {item['data_hora']}{tag_recente} | Base: {item['arquivo_original']}\n"
                    f"Regras: {item['termos']}\n"
                    f"Linhas: {item['linhas']}"
                )

                lbl_info = ctk.CTkLabel(
                    card,
                    text=texto_info,
                    justify="left",
                    font=ctk.CTkFont(size=12, weight="bold" if is_recente else "normal"),
                )
                lbl_info.pack(side="left", padx=10, pady=10)

                frame_botoes = ctk.CTkFrame(card, fg_color="transparent")
                frame_botoes.pack(side="right", padx=10)

                caminho_exp = item.get("caminho_exportacao", "")
                if os.path.exists(caminho_exp):
                    btn_abrir = ctk.CTkButton(
                        frame_botoes,
                        text="Abrir Planilha",
                        width=120,
                        fg_color="#27ae60",
                        hover_color="#2ecc71",
                        command=lambda c=caminho_exp, rid=item["id"]: self.abrir_planilha_os(c, rid),
                    )
                    btn_abrir.pack(side="left", padx=5)

                btn_exportar = ctk.CTkButton(
                    frame_botoes,
                    text="Exportar",
                    width=130,
                    command=lambda res=item["caminho_resultado_imutavel"], rid=item["id"]: self.exportar_do_historico(res, rid),
                )
                btn_exportar.pack(side="left", padx=5)

        except Exception:
            pass

    def abrir_planilha_os(self, caminho: str, registro_id: str | None = None) -> None:
        try:
            if sys.platform == "win32":
                os.startfile(caminho)
            elif sys.platform == "darwin":
                subprocess.call(["open", caminho])
            else:
                subprocess.call(["xdg-open", caminho])
        except Exception as erro:
            if registro_id:
                motor_dados.atualizar_caminho_exportacao_historico(registro_id, "")
                self.carregar_historico()
            messagebox.showerror(
                "Erro",
                (
                    "Nao foi possivel abrir o arquivo.\n"
                    "Ele pode ter sido movido ou excluido.\n\n"
                    f"Detalhe: {str(erro)}"
                ),
            )

    def exportar_do_historico(self, caminho_resultado_imutavel: str, registro_id: str) -> None:
        if not os.path.exists(caminho_resultado_imutavel):
            messagebox.showerror("Erro", "Arquivo imutavel nao encontrado no cofre do sistema.")
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        nome_sugerido = motor_dados.gerar_nome_recuperacao(timestamp)

        caminho_salvar = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            initialfile=nome_sugerido,
            filetypes=[("Excel", "*.xlsx")],
        )

        if caminho_salvar:
            try:
                motor_dados.exportar_resultado_historico(caminho_resultado_imutavel, caminho_salvar)
                motor_dados.atualizar_caminho_exportacao_historico(registro_id, caminho_salvar)
                self.carregar_historico(destaque_id=registro_id)
                messagebox.showinfo("Sucesso", "Recuperacao do historico concluida com sucesso!")
            except Exception as erro:
                messagebox.showerror("Erro", f"Falha ao exportar: {str(erro)}")

    def restaurar_interface(self) -> None:
        self.btn_processar.configure(state="normal", fg_color="green")
        self.combo_bases.configure(state="normal")
        self.btn_add_filtro.configure(state="normal")
        self.btn_converter_sem_filtro.configure(state="normal")
        self.btn_exportar_csv_base.configure(state="normal")
        self._loading_main_ativo = False
        if self.canvas_loading_main:
            self.canvas_loading_main.pack_forget()