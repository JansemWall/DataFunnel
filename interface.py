import os
import subprocess
import sys
import threading
from datetime import datetime

import customtkinter as ctk
from tkinter import filedialog, messagebox

import motor_dados
from atualizador import baixar_e_aplicar_update, verificar_nova_versao
from config import VERSAO_ATUAL, inicializar_sistema

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")


class BuscadorApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        self.title(f"Sistema Avancado de Filtros de Dados - v{VERSAO_ATUAL}")
        self.geometry("750x850")

        self.caminho_base_ativa = ""
        self.is_base_no_cofre = False
        self.filtros_widgets = []
        self.stop_event = threading.Event()
        self.thread_processamento = None

        inicializar_sistema()

        self.label_titulo = ctk.CTkLabel(
            self,
            text="Filtro de Planilhas em Funil",
            font=ctk.CTkFont(size=22, weight="bold"),
        )
        self.label_titulo.pack(pady=(15, 5))

        self.tabview = ctk.CTkTabview(self, width=710, height=750)
        self.tabview.pack(padx=20, pady=10, fill="both", expand=True)

        self.tab_pesquisa = self.tabview.add("Nova Pesquisa")
        self.tab_historico = self.tabview.add("Historico de Resultados")

        self.configurar_aba_pesquisa()
        self.configurar_aba_historico()

        self.tabview.configure(command=self.ao_mudar_aba)
        self.protocol("WM_DELETE_WINDOW", self.ao_fechar_aplicacao)

        if getattr(sys, "frozen", False):
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
        except Exception as erro:
            print(f"Erro ao verificar atualizacoes: {erro}")

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
        self.barra_progresso = ctk.CTkProgressBar(self.frame_status, mode="indeterminate", width=400)

    def ao_selecionar_base(self, escolha: str) -> None:
        if escolha == "+ Carregar novo arquivo do computador...":
            caminho = filedialog.askopenfilename(filetypes=[("Arquivos de Dados", "*.csv *.xlsx *.xls")])
            if caminho:
                self.caminho_base_ativa = caminho
                self.is_base_no_cofre = False
                nome = os.path.basename(caminho)
                self.label_arquivo.configure(text=f"Arquivo externo selecionado: {nome}", text_color="#f39c12")
                self.combo_bases.set("Arquivo Externo Selecionado")
            else:
                self.combo_bases.set("Selecione uma base...")
        else:
            self.caminho_base_ativa = self.bases_salvas[escolha]
            self.is_base_no_cofre = True
            self.label_arquivo.configure(text=f"Base carregada do cache local: {escolha}", text_color="#2ecc71")

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
        entry_col = ctk.CTkTextbox(frame_col, height=70, wrap="word")
        entry_col.pack(fill="x")

        frame_term = ctk.CTkFrame(frame_inputs, fg_color="transparent")
        frame_term.pack(side="right", fill="both", expand=True, padx=(0, 5))
        ctk.CTkLabel(frame_term, text="Procurar termo(s) (cole a lista aqui):").pack(anchor="w")
        entry_term = ctk.CTkTextbox(frame_term, height=70, wrap="word")
        entry_term.pack(fill="x")

        novo_widget = {
            "frame_container": linha_frame_container,
            "entry_coluna": entry_col,
            "entry_termos": entry_term,
            "label_titulo": lbl_titulo_linha,
        }
        self.filtros_widgets.append(novo_widget)
        return novo_widget

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
        self.label_status.configure(text="Iniciando processamento...", text_color="white")

        self.barra_progresso.pack(pady=5)
        self.barra_progresso.start()

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
                status_callback=lambda txt: self.label_status.configure(text=txt),
            )

            df_filtrado = motor_dados.filtrar_em_lotes(
                caminho_origem_imutavel,
                regras_de_busca,
                stop_event=self.stop_event,
                status_callback=lambda txt: self.label_status.configure(text=txt),
            )

            qtd_linhas = len(df_filtrado)

            self.label_status.configure(text="Salvando resultado e historico...")
            caminho_resultado_imutavel = motor_dados.salvar_resultado_csv(df_filtrado, timestamp)

            self.label_status.configure(text="Exportando arquivo final...")
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

            self.label_status.configure(text="Concluido!", text_color="green")

            if self.winfo_exists():
                self.after(0, lambda: self.finalizar_sucesso_transicao(timestamp))

        except RuntimeError as erro:
            if str(erro) != "PROCESSAMENTO_CANCELADO":
                self.label_status.configure(text="Erro!", text_color="red")
                if self.winfo_exists():
                    self.after(
                        0,
                        lambda e=erro: messagebox.showerror(
                            "Erro de Processamento",
                            f"Ocorreu um erro critico:\n{str(e)}",
                        ),
                    )
        except Exception as erro:
            self.label_status.configure(text="Erro!", text_color="red")
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
                self.after(0, self.restaurar_interface)

    def ao_fechar_aplicacao(self) -> None:
        self.stop_event.set()

        if self.thread_processamento and self.thread_processamento.is_alive():
            self.thread_processamento.join(timeout=2)

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
        self.barra_progresso.stop()
        self.barra_progresso.pack_forget()
